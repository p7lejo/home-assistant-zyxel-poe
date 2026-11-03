"""Config flow for ZyXEL PoE integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .switch import SCAN_INTERVAL, ZyxelPoeData
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import aiohttp

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ZyxelPoeConfigFlow(config_entries.ConfigFlow, domain="zyxel_poe"):
    """Handle a config flow for ZyXEL PoE."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                await self.async_set_unique_id(user_input[CONF_HOST].strip().lower())
                self._abort_if_unique_id_configured()

                # Validate the connection using the same constructor contract
                # as the platform setup.
                session = async_create_clientsession(
                    self.hass, cookie_jar=aiohttp.CookieJar(unsafe=True)
                )
                poe_data = ZyxelPoeData(
                    self.hass,
                    user_input[CONF_HOST],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    SCAN_INTERVAL,
                    session,
                )
                
                try:
                    await poe_data._login()
                    # Create entry
                    return self.async_create_entry(
                        title=f"ZyXEL PoE {user_input[CONF_HOST]}",
                        data=user_input
                    )
                except Exception as ex:
                    _LOGGER.error(f"Login failed: {ex}")
                    errors["base"] = "invalid_auth"
            except Exception as ex:
                _LOGGER.error(f"Connection failed: {ex}")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )
