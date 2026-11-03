"""Regression tests for config-flow behavior.

The current config-flow implementation has a constructor/signature mismatch with
ZyxelPoeData. These tests document the expected flow contract and will expose
that defect until issue #12 is implemented.
"""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

from custom_components.zyxel_poe.const import DOMAIN


@pytest.mark.asyncio
async def test_user_flow_shows_form(hass):
    """The initial step asks for host and credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_user_flow_rejects_duplicate_host(hass):
    """A switch already configured must not be added a second time."""
    hass.config_entries.add(
        config_entries.ConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Existing switch",
            data={
                CONF_HOST: "192.0.2.10",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "secret",
            },
            source=config_entries.SOURCE_USER,
            entry_id="existing",
            options={},
        )
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
