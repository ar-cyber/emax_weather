"""
Emax Weather Station integration for Home Assistant.

This integration connects to Emax weather stations via the cloud API.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Final

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, SCAN_INTERVAL
from .api_client import EmaxWeatherAPIClient

_LOGGER: logging.Logger = logging.getLogger(__name__)

PLATFORMS: Final = [Platform.SENSOR]

SERVICE_REFRESH_WEATHER = "refresh_weather"
SERVICE_SCHEMA = vol.Schema({})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Emax Weather from a config entry."""
    
    hass.data.setdefault(DOMAIN, {})
    
    # Create API client
    api_client = EmaxWeatherAPIClient(
        email=entry.data["email"],
        password=entry.data["password"],
        base_url=entry.data.get("base_url", "https://app.emaxlife.net/V1.0")
    )
    
    # Create coordinator
    coordinator = EmaxWeatherCoordinator(hass, api_client)
    
    # Initial refresh
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api_client": api_client,
    }
    
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Setup services
    async def handle_refresh_weather(call: ServiceCall) -> None:
        """Handle refresh weather service call."""
        await coordinator.async_request_refresh()
        _LOGGER.info("Weather data refresh requested")
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_WEATHER,
        handle_refresh_weather,
        schema=SERVICE_SCHEMA,
    )
    
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        api_client = hass.data[DOMAIN][entry.entry_id]["api_client"]
        await api_client.async_close()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class EmaxWeatherCoordinator(DataUpdateCoordinator):
    """Coordinator for Emax Weather Station data."""

    def __init__(self, hass: HomeAssistant, api_client: EmaxWeatherAPIClient) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Emax Weather Station",
            update_interval=timedelta(minutes=SCAN_INTERVAL),
        )
        self.api_client = api_client

    async def _async_update_data(self) -> dict:
        """Fetch data from API."""
        try:
            # Ensure we have a valid token
            if not self.api_client.token:
                await self.api_client.async_login()
            
            # Get realtime weather
            weather_data = await self.api_client.async_get_realtime_weather()
            
            if not weather_data:
                raise ValueError("No weather data returned")
            
            return weather_data
        except asyncio.TimeoutError as err:
            raise UpdateFailed("Timeout communicating with API") from err
        except ValueError as err:
            raise UpdateFailed(f"Invalid data from API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error updating data: {err}") from err
