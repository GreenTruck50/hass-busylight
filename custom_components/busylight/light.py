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
)
from .coordinator import BusylightCoordinator

_LOGGER = logging.getLogger(__name__)

# Ignore coordinator overwrites for this long after a local command
_ASSUMED_STATE_SECONDS = 3.0
_DEFAULT_RGB = (0, 255, 0)


def _rgb_to_hex(rgb: tuple[int, int, int] | list[int]) -> str:
    """Convert RGB tuple to hex string the API accepts."""
    r, g, b = (max(0, min(255, int(c))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _brightness_to_dim(brightness: int | None) -> float:
    """Convert HA brightness (0-255) to API dim (0.0-1.0)."""
    if brightness is None:
        return 1.0
    return max(0.05, min(1.0, brightness / 255.0))


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
        self._rgb_color = _parse_rgb(light_data.get("rgb")) or _DEFAULT_RGB
        self._brightness = 255
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

        # Only adopt is_on from API when we are in solid (no effect) mode,
        # or when the API clearly agrees we are on.
        if self._effect == EFFECT_OFF:
            self._is_on = api_on
            if api_on and api_rgb is not None:
                self._rgb_color = api_rgb
            elif not api_on:
                # Off: keep last known color so the UI does not flash black
                pass
        else:
            # Effect running: trust local on + color; only update if API has a real color
            self._is_on = True
            if api_rgb is not None:
                self._rgb_color = api_rgb

        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on / set color / start effect."""
        effect = kwargs.get(ATTR_EFFECT, self._effect)
        if effect is None:
            effect = EFFECT_OFF

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
                        self.light_id, color=color, dim=dim, speed="medium", count=0
                    )
                elif effect == EFFECT_RAINBOW:
                    await self.client.async_rainbow(
                        self.light_id, dim=dim, speed="medium"
                    )
                elif effect == EFFECT_PULSE:
                    await self.client.async_pulse(
                        self.light_id, color=color, dim=dim, speed="medium", count=0
                    )
                elif effect == EFFECT_FLI:
                    await self.client.async_fli(
                        self.light_id, color=color, dim=dim, speed="medium", count=0
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
            self._effect = effect
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
