"""Binary sensor platform for Busylight health check."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BusylightCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Busylight health binary sensor."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BusylightCoordinator = data["coordinator"]

    async_add_entities([BusylightHealthSensor(coordinator, entry)])


class BusylightHealthSensor(CoordinatorEntity[BusylightCoordinator], BinarySensorEntity):
    """Binary sensor reflecting Busylight API system health."""

    _attr_has_entity_name = True
    _attr_name = "Health"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: BusylightCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entry = entry
        host = entry.data.get("host", "busylight")
        port = entry.data.get("port", 8000)

        self._attr_unique_id = f"{entry.unique_id}_health"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=f"Busylight ({host})",
            manufacturer="Busylight for Humans",
            model="Web API host",
            configuration_url=f"http://{host}:{port}/docs",
        )

    @property
    def is_on(self) -> bool:
        """Return True when the API reports healthy status."""
        health = (self.coordinator.data or {}).get("health") or {}
        status = str(health.get("status", "")).lower()
        return status == "healthy" and self.coordinator.last_update_success

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict:
        health = (self.coordinator.data or {}).get("health") or {}
        return {
            "status": health.get("status"),
            "lights_available": health.get("lights_available"),
            "timestamp": health.get("timestamp"),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
