"""Regression tests for config-flow behavior."""

from unittest.mock import AsyncMock

import pytest

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zyxel_poe.const import DOMAIN


@pytest.mark.asyncio
async def test_user_flow_shows_form(hass, enable_custom_integrations):
    """The initial step asks for host and credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_user_flow_rejects_duplicate_host(hass, enable_custom_integrations):
    """A switch already configured must not be added a second time."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        title="Existing switch",
        unique_id="192.0.2.10",
        data={
            CONF_HOST: "192.0.2.10",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
        },
    )
    existing.add_to_hass(hass)

    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        user_input={
            CONF_HOST: "192.0.2.10",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
        },
    )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_user_flow_validates_credentials_and_creates_entry(
    hass, enable_custom_integrations, monkeypatch
):
    """A valid login creates a config entry with the supplied host."""
    from custom_components.zyxel_poe import config_flow

    login = AsyncMock()
    monkeypatch.setattr(config_flow.ZyxelPoeData, "_login", login)

    # Keep this test focused on flow validation. Creating the entry must not
    # start the integration setup lifecycle; that is covered by test_init.py.
    monkeypatch.setattr(
        hass.config_entries,
        "async_setup",
        AsyncMock(return_value=True),
    )

    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        user_input={
            CONF_HOST: "192.0.2.11",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
        },
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_HOST] == "192.0.2.11"
    login.assert_awaited_once()
