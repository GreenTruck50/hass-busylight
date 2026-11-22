"""Light platform for Busylight for Humans."""

from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BusylightApiClient
from .const import (
    DOMAIN,
    EFFECT_BLINK,
    EFFECT_FLI,
    EFFECT_OFF,
    EFFECT_PULSE,
    EFFECT_RAINBOW,
    SUPPORTED_EFFECTS,
    effect_name,
    parse_effect,
)
from .coordinator import BusylightCoordinator

_LOGGER = logging.getLogger(__name__)

# Ignore coordinator overwrites for this long after a local command
_ASSUMED_STATE_SECONDS = 3.0
_DEFAULT_RGB = (0, 255, 0)

# busyserve folds `dim` into the color before driving the hardware and rounds
# every channel independently, so comparing reported colors needs a tolerance
# that grows a little with the brightness of the color.
_DIM_TOLERANCE = 2.0
_DIM_TOLERANCE_RATIO = 0.03


def _rgb_to_hex(rgb: tuple[int, int, int] | list[int]) -> str:
    """Convert RGB tuple to hex string the API accepts."""
    r, g, b = (max(0, min(255, int(c))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _brightness_to_dim(brightness: int | None) -> float:
    """Convert HA brightness (0-255) to API dim (0.0-1.0)."""
    if brightness is None:
        return 1.0
    return max(0.0, min(1.0, brightness / 255.0))


def _dim_from_rgb(rgb: tuple[int, int, int]) -> float:
    """Best available guess of the `dim` behind a reported RGB color.

    Upstream has no hardware brightness: `dim` is applied by multiplying every
    channel of the requested color (``scale_color`` in ``busylight/color.py``)
    and ``GET /api/v1/lights`` has no ``dim`` field at all — it only reports
    ``rgb``/``is_on``. The brightest channel is therefore the only dim hint.
    """
    return max(0, min(255, max(rgb))) / 255.0


def _split_dim(rgb: tuple[int, int, int]) -> tuple[tuple[int, int, int], int]:
    """Split a color reported by the API into (color, brightness).

    Home Assistant expects `rgb_color` to describe the hue/saturation and to be
    independent of brightness, so the dim upstream baked into the color is
    lifted back out: the brightest channel is restored to 255 and the removed
    factor is reported as the entity's brightness instead.
    """
    dim = _dim_from_rgb(rgb)
    if dim <= 0.0:
        return rgb, 0

    scaled = tuple(max(0, min(255, round(c / dim))) for c in rgb)
    return (scaled[0], scaled[1], scaled[2]), int(round(dim * 255))


def _is_dimmed_version(
    reported: tuple[int, int, int], color: tuple[int, int, int]
) -> bool:
    """Return True if `reported` is `color` multiplied by one dim factor.

    Used to tell "the same color, dimmed by someone else" (move the difference
    onto the HA brightness slider, keep the color) from "a different color"
    (adopt it). The per-channel tolerance absorbs upstream's independent
    channel rounding at low dim values.
    """
    max_reported = max(reported)
    max_color = max(color)
    if max_reported == 0 or max_color == 0:
        return False

    dim = max_reported / max_color
    if dim > 1.0:
        return False

    tolerance = _DIM_TOLERANCE + _DIM_TOLERANCE_RATIO * max_reported
    return all(
        abs(expected - actual) <= tolerance
        for expected, actual in zip(
            (channel * dim for channel in color), reported, strict=True
        )
    )


def _parse_rgb(value: Any) -> tuple[int, int, int] | None:
    """Parse API rgb; return None if missing or pure black."""
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        rgb = (int(value[0]), int(value[1]), int(value[2]))
    except (TypeError, ValueError):
        return None
    if rgb == (0, 0, 0):
        return None
    return rgb


def _lights_map(coordinator: BusylightCoordinator) -> dict[int, dict[str, Any]]:
    """Return the lights dict from coordinator data."""
    data = coordinator.data or {}
    lights = data.get("lights")
    if isinstance(lights, dict):
        return lights
    return {k: v for k, v in data.items() if isinstance(k, int)}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Busylight lights from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BusylightCoordinator = data["coordinator"]
    client: BusylightApiClient = data["client"]

    if not coordinator.data:
        await coordinator.async_request_refresh()

    entities: list[BusylightLight] = []
    for light_id, light_data in _lights_map(coordinator).items():
        entities.append(
            BusylightLight(
                coordinator=coordinator,
                client=client,
                entry=entry,
                light_id=light_id,
                light_data=light_data,
            )
        )

    async_add_entities(entities)


class BusylightLight(CoordinatorEntity[BusylightCoordinator], LightEntity):
    """Representation of a single Busylight device as an RGB light with effects."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = SUPPORTED_EFFECTS

    def __init__(
        self,
        coordinator: BusylightCoordinator,
        client: BusylightApiClient,
        entry: ConfigEntry,
        light_id: int,
        light_data: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self.client = client
        self.entry = entry
        self.light_id = light_id
        self._light_data = light_data
        self._assumed_until = 0.0

        name = light_data.get("name") or f"Light {light_id}"

        self._attr_unique_id = f"{entry.unique_id}_{light_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.unique_id}_{light_id}")},
            name=name,
            manufacturer="Busylight for Humans",
            model=name,
            via_device=(DOMAIN, entry.unique_id),
            configuration_url=(
                f"http://{entry.data.get('host')}:{entry.data.get('port', 8000)}/docs"
            ),
        )

        self._is_on = bool(light_data.get("is_on", False))
        api_rgb = _parse_rgb(light_data.get("rgb"))
        if api_rgb is None:
            self._rgb_color = _DEFAULT_RGB
            self._brightness = 255
        else:
            # The reported color already has upstream's `dim` folded into it,
            # so split it into a pure color plus brightness instead of showing
            # a dark color at full brightness.
            self._rgb_color, self._brightness = _split_dim(api_rgb)
        self._effect = EFFECT_OFF

    def _mark_assumed(self) -> None:
        """Protect optimistic state from the next coordinator poll."""
        self._assumed_until = time.monotonic() + _ASSUMED_STATE_SECONDS

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.light_id in _lights_map(
            self.coordinator
        )

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def brightness(self) -> int | None:
        return self._brightness

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return self._rgb_color

    @property
    def effect(self) -> str | None:
        return self._effect

    @callback
    def _handle_coordinator_update(self) -> None:
        # Keep local optimistic state for a short window after user commands.
        # API status during effects often reports black / is_on=false and causes UI glitches.
        if time.monotonic() < self._assumed_until:
            self.async_write_ha_state()
            return

        data = _lights_map(self.coordinator).get(self.light_id)
        if data is None:
            self.async_write_ha_state()
            return

        self._light_data = data
        api_on = bool(data.get("is_on", False))
        api_rgb = _parse_rgb(data.get("rgb"))

        if self._effect != EFFECT_OFF:
            # Effect running: the reported rgb is whichever animation frame is
            # lit right now (pulse ramps black -> color -> black) and is_on is
            # often false, so keep the locally commanded color and brightness.
            self._is_on = True
            self.async_write_ha_state()
            return

        # Solid color mode: is_on comes from the API, and the reported color is
        # the commanded color with `dim` already multiplied into every channel.
        self._is_on = api_on
        if api_rgb is not None:
            color = self._rgb_color or _DEFAULT_RGB
            if _is_dimmed_version(api_rgb, color):
                # Same color, only dim changed (e.g. dimmed by the CLI or
                # another client): keep the color, move the difference onto the
                # Home Assistant brightness slider.
                self._brightness = int(round(_dim_from_rgb(api_rgb) * 255))
            else:
                # A genuinely different color: adopt it, but keep the brightness
                # interpretation so rgb_color stays independent of dim.
                self._rgb_color, self._brightness = _split_dim(api_rgb)
        # Nothing usable reported (off / mid-effect black): keep the last known
        # color and brightness so the UI does not flash black.

        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on / set color / start effect."""
        effect, speed = parse_effect(kwargs.get(ATTR_EFFECT, self._effect))

        brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
        if brightness is None:
            brightness = 255

        rgb = kwargs.get(ATTR_RGB_COLOR, self._rgb_color or _DEFAULT_RGB)
        if not rgb or rgb == (0, 0, 0):
            rgb = self._rgb_color if self._rgb_color and self._rgb_color != (0, 0, 0) else _DEFAULT_RGB

        dim = _brightness_to_dim(brightness)
        color = _rgb_to_hex(rgb)

        try:
            # Leaving an effect for solid color: stop the effect first so the
            # device is not stuck mid-animation reporting black.
            if (
                self._effect != EFFECT_OFF
                and (effect == EFFECT_OFF or effect is None)
                and (ATTR_EFFECT in kwargs or ATTR_RGB_COLOR in kwargs or ATTR_BRIGHTNESS in kwargs)
            ):
                await self.client.async_turn_off(self.light_id)

            if effect and effect != EFFECT_OFF:
                if effect == EFFECT_BLINK:
                    await self.client.async_blink(
                        self.light_id, color=color, dim=dim, speed=speed, count=0
                    )
                elif effect == EFFECT_RAINBOW:
                    await self.client.async_rainbow(
                        self.light_id, dim=dim, speed=speed
                    )
                elif effect == EFFECT_PULSE:
                    await self.client.async_pulse(
                        self.light_id, color=color, dim=dim, speed=speed, count=0
                    )
                elif effect == EFFECT_FLI:
                    # FLI ("GetFlashyIndication"): alternating red / blue flash,
                    # served by the v1 flash endpoint.
                    await self.client.async_fli(
                        self.light_id,
                        color_a="red",
                        color_b="blue",
                        dim=dim,
                        speed=speed,
                        count=0,
                    )
                else:
                    await self.client.async_turn_on(
                        self.light_id, color=color, dim=dim
                    )
                    effect = EFFECT_OFF
            else:
                await self.client.async_turn_on(self.light_id, color=color, dim=dim)
                effect = EFFECT_OFF

            self._is_on = True
            self._brightness = int(brightness)
            self._rgb_color = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
            self._effect = effect_name(effect, speed)
            self._mark_assumed()
            self.async_write_ha_state()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed to turn on light %s: %s", self.light_id, err)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        try:
            await self.client.async_turn_off(self.light_id)
            self._is_on = False
            self._effect = EFFECT_OFF
            self._mark_assumed()
            self.async_write_ha_state()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed to turn off light %s: %s", self.light_id, err)
            raise
