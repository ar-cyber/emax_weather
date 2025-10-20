"""Config flow for Emax Weather integration."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DEFAULT_BASE_URL
from .api_client import EmaxWeatherAPIClient

_LOGGER = logging.getLogger(__name__)


class EmaxWeatherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Emax Weather integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate credentials
            client = EmaxWeatherAPIClient(
                email=user_input["email"],
                password=user_input["password"],
                base_url=DEFAULT_BASE_URL
            )

            try:
                if not await client.async_login():
                    errors["base"] = "invalid_auth"
                else:
                    # Check if entry already exists
                    await self.async_set_unique_id(user_input["email"])
                    self._abort_if_unique_id_configured()

                    await client.async_close()

                    return self.async_create_entry(
                        title=f"Emax Weather ({user_input['email']})",
                        data=user_input,
                    )
            except Exception as err:
                _LOGGER.error(f"Error validating credentials: {err}")
                errors["base"] = "cannot_connect"
            finally:
                await client.async_close()

        data_schema = vol.Schema(
            {
                vol.Required("email"): str,
                vol.Required("password"): str,
                vol.Optional("base_url", default=DEFAULT_BASE_URL): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "learn_more": "https://github.com/your-username/emax-weather-homeassistant"
            },
        )

    async def async_step_import(self, import_data: Dict[str, Any]) -> FlowResult:
        """Import a config entry."""
        return await self.async_step_user(import_data)


class EmaxWeatherOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Emax Weather integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    "scan_interval",
                    default=self.config_entry.options.get("scan_interval", 10),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                vol.Optional(
                    "temperature_unit",
                    default=self.config_entry.options.get("temperature_unit", "C"),
                ): vol.In(["C", "F"]),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)


async def async_options_init(config_entry: config_entries.ConfigEntry) -> None:
    """Set up options flow."""
    config_entry.add_update_listener(async_update_listener)


async def async_update_listener(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
