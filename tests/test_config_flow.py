"""Regression tests for config-flow behavior.

The duplicate-host test is an expected failure until issue #12 is implemented.
"""

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
@pytest.mark.xfail(
    strict=True,
    reason="Known defect tracked in issue #12: duplicate host is not rejected.",
)
async def test_user_flow_rejects_duplicate_host(hass):
    """A switch already configured must not be added a second time."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        title="Existing switch",
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
