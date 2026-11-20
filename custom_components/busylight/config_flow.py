"""Config flow for Busylight for Humans."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .api import BusylightApiClient, BusylightApiError
from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Returns info suitable for title and unique_id.
    """
    client = BusylightApiClient(
        hass,
        host=data[CONF_HOST],
        port=data.get(CONF_PORT, DEFAULT_PORT),
        username=data.get(CONF_USERNAME),
        password=data.get(CONF_PASSWORD),
    )
    try:
        health = await client.async_get_health()
        lights = await client.async_get_lights()
    except BusylightApiError as err:
        raise ValueError(str(err)) from err

    return {
        "title": f"Busylight ({data[CONF_HOST]})",
        "lights_available": health.get("lights_available", len(lights)),
        "host": data[CONF_HOST],
        "port": data.get(CONF_PORT, DEFAULT_PORT),
    }


class BusylightConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Busylight."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except ValueError as err:
                _LOGGER.debug("Validation failed: %s", err)
                if "Authentication" in str(err):
                    errors["base"] = "invalid_auth"
                elif "Connection" in str(err) or "connect" in str(err).lower():
                    errors["base"] = "cannot_connect"
                else:
                    errors["base"] = "unknown"
            else:
                unique_id = f"{info['host']}:{info['port']}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return BusylightOptionsFlow(config_entry)


class BusylightOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Busylight."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "scan_interval",
                        default=self.config_entry.options.get(
                            "scan_interval", 10
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                }
            ),
        )
