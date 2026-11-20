"""DataUpdateCoordinator for Busylight."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BusylightApiClient, BusylightApiError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class BusylightCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Coordinator that polls the Busylight API for light status."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: BusylightApiClient,
    ) -> None:
        self.client = client
        self.entry = entry
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        """Fetch latest light status from the API."""
        try:
            lights = await self.client.async_get_lights()
        except BusylightApiError as err:
            raise UpdateFailed(f"Error communicating with Busylight API: {err}") from err

        result: dict[int, dict[str, Any]] = {}
        for light in lights:
            light_id = light.get("light_id")
            if light_id is None:
                continue
            result[int(light_id)] = light
        return result
