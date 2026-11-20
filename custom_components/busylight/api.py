"""Async client for the Busylight for Humans Web API."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_PREFIX,
    EFFECT_FLASH_PATH,
    EFFECT_PULSE_PATH,
    EFFECT_RAINBOW_PATH,
    LIGHT_BLINK_PATH,
    LIGHT_OFF_PATH,
    LIGHT_ON_PATH,
    LIGHT_STATUS_PATH,
    LIGHTS_PATH,
    SYSTEM_HEALTH_PATH,
)

_LOGGER = logging.getLogger(__name__)


class BusylightApiError(Exception):
    """Base exception for Busylight API errors."""


class BusylightApiClient:
    """Client for interacting with a Busylight Web API server."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int = 8000,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.hass = hass
        self.host = host.rstrip("/")
        self.port = port
        self.base_url = f"http://{self.host}:{self.port}"
        self._auth: aiohttp.BasicAuth | None = None
        if username and password:
            self._auth = aiohttp.BasicAuth(username, password)
        self._session: aiohttp.ClientSession | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = async_get_clientsession(self.hass)
        return self._session

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with self.session.request(
                method,
                url,
                json=json_data,
                auth=self._auth,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 401:
                    raise BusylightApiError("Authentication failed")
                if resp.status == 404:
                    raise BusylightApiError(f"Resource not found: {path}")
                if resp.status == 503:
                    raise BusylightApiError("No lights available on the host")
                if resp.status >= 400:
                    text = await resp.text()
                    raise BusylightApiError(f"API error {resp.status}: {text}")
                if resp.content_type == "application/json":
                    return await resp.json()
                return await resp.text()
        except aiohttp.ClientError as err:
            raise BusylightApiError(f"Connection error: {err}") from err

    async def async_get_health(self) -> dict[str, Any]:
        """Return system health."""
        return await self._request("GET", SYSTEM_HEALTH_PATH)

    async def async_get_lights(self) -> list[dict[str, Any]]:
        """Return list of all lights and their status."""
        data = await self._request("GET", LIGHTS_PATH)
        if isinstance(data, list):
            return data
        return data.get("lights", data) if isinstance(data, dict) else []

    async def async_get_light(self, light_id: int) -> dict[str, Any]:
        """Return status of a single light."""
        path = LIGHT_STATUS_PATH.format(light_id=light_id)
        return await self._request("GET", path)

    async def async_turn_on(
        self,
        light_id: int,
        color: str = "green",
        dim: float = 1.0,
        led: int = 0,
    ) -> dict[str, Any]:
        """Turn a light on with the given color and brightness factor."""
        path = LIGHT_ON_PATH.format(light_id=light_id)
        payload = {"color": color, "dim": max(0.0, min(1.0, dim)), "led": led}
        return await self._request("POST", path, payload)

    async def async_turn_off(self, light_id: int) -> dict[str, Any]:
        """Turn a light off."""
        path = LIGHT_OFF_PATH.format(light_id=light_id)
        return await self._request("POST", path, {})

    async def async_blink(
        self,
        light_id: int,
        color: str = "red",
        dim: float = 1.0,
        speed: str = "slow",
        count: int = 0,
        led: int = 0,
    ) -> dict[str, Any]:
        """Start a blink effect."""
        path = LIGHT_BLINK_PATH.format(light_id=light_id)
        payload = {
            "color": color,
            "dim": max(0.0, min(1.0, dim)),
            "speed": speed,
            "count": count,
            "led": led,
        }
        return await self._request("POST", path, payload)

    async def async_rainbow(
        self,
        light_id: int,
        dim: float = 1.0,
        speed: str = "slow",
        led: int = 0,
    ) -> dict[str, Any]:
        """Start rainbow effect."""
        path = EFFECT_RAINBOW_PATH.format(light_id=light_id)
        payload = {"dim": max(0.0, min(1.0, dim)), "speed": speed, "led": led}
        return await self._request("POST", path, payload)

    async def async_pulse(
        self,
        light_id: int,
        color: str = "red",
        dim: float = 1.0,
        speed: str = "slow",
        count: int = 0,
        led: int = 0,
    ) -> dict[str, Any]:
        """Start pulse / breathing effect."""
        path = EFFECT_PULSE_PATH.format(light_id=light_id)
        payload = {
            "color": color,
            "dim": max(0.0, min(1.0, dim)),
            "speed": speed,
            "count": count,
            "led": led,
        }
        return await self._request("POST", path, payload)

    async def async_flash(
        self,
        light_id: int,
        color_a: str = "red",
        color_b: str = "blue",
        dim: float = 1.0,
        speed: str = "slow",
        count: int = 0,
        led: int = 0,
    ) -> dict[str, Any]:
        """Start flash (alternate two colors) effect."""
        path = EFFECT_FLASH_PATH.format(light_id=light_id)
        payload = {
            "color_a": color_a,
            "color_b": color_b,
            "dim": max(0.0, min(1.0, dim)),
            "speed": speed,
            "count": count,
            "led": led,
        }
        return await self._request("POST", path, payload)

    async def async_close(self) -> None:
        """Close the client (session is shared with HA)."""
        self._session = None
