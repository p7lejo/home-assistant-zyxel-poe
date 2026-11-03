"""Tests for switch data handling and entities."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.exceptions import PlatformNotReady

from custom_components.zyxel_poe.switch import ZyxelPoeSwitch, encode


def test_encode_returns_fixed_length_obfuscated_password():
    """The Zyxel login form expects a 321-character encoded value."""
    assert len(encode("secret")) == 321


def test_encode_embeds_password_characters_in_reverse_order(monkeypatch):
    """Random padding must not change the embedded password sequence."""
    monkeypatch.setattr("custom_components.zyxel_poe.switch.random", lambda: 0)
    encoded = encode("abc")
    assert "c" in encoded
    assert "b" in encoded
    assert "a" in encoded


def test_switch_availability_requires_device_and_port(poe_data):
    """A switch entity is only available while the device and port are available."""
    poe_data.available = True
    poe_data.ports = {"1": {"state": STATE_ON}}
    entity = ZyxelPoeSwitch(poe_data, "192.0.2.10", "1")

    assert entity.available is True
    assert entity.is_on is True

    poe_data.available = False
    assert entity.available is False


def test_switch_unique_id_is_stable(poe_data):
    """Existing entity registry IDs must not change."""
    entity = ZyxelPoeSwitch(poe_data, "192.0.2.10", "7")
    assert entity.unique_id == "192.0.2.10_port_7"


@pytest.mark.asyncio
async def test_failed_initial_poll_raises_platform_not_ready(poe_data):
    """A failed first poll must prevent a partially initialized integration."""
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = False
    response.status = 503
    response.text.return_value = "Service unavailable"
    poe_data._session.get = AsyncMock(return_value=response)

    with pytest.raises(PlatformNotReady):
        await poe_data._async_update()

    assert poe_data.available is False
    assert poe_data.ports == {}


@pytest.mark.asyncio
async def test_runtime_poll_failure_marks_data_unavailable_and_keeps_last_snapshot(
    poe_data,
):
    """A later communication failure must not replace the last valid port snapshot."""
    poe_data._initial_update_succeeded = True
    poe_data.available = True
    previous = {"1": {"port": "1", "state": STATE_ON}}
    poe_data.ports = previous
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = False
    response.status = 503
    response.text.return_value = "Service unavailable"
    poe_data._session.get = AsyncMock(return_value=response)

    await poe_data._async_update()

    assert poe_data.available is False
    assert poe_data.ports is previous


@pytest.mark.asyncio
async def test_successful_poll_restores_availability(poe_data, monkeypatch):
    """A valid port table restores availability after a previous failure."""
    from bs4 import BeautifulSoup

    # Three tables are expected by the current firmware parser; the third table
    # contains one 12-cell port row.
    cells = [
        "x", "x", "1", "Enable", "Class 3", "High", "On",
        "1200", "30000", "Always", "Active", "x",
    ]
    row = "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"
    html = f"<table></table><table></table><table>{row}</table>"

    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = html
    poe_data._session.get = AsyncMock(return_value=response)
    poe_data._async_update_device_info = AsyncMock()
    poe_data._device_info_loaded = True

    await poe_data._async_update()

    assert poe_data.available is True
    assert poe_data.ports["1"]["state"] == STATE_ON
    assert poe_data.ports["1"]["current_power_w"] == 1.2


@pytest.mark.asyncio
async def test_empty_or_unrecognized_port_table_is_rejected(poe_data):
    """A response without recognizable port rows must not be accepted."""
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = "<table></table><table></table><table></table>"
    poe_data._session.get = AsyncMock(return_value=response)

    with pytest.raises(PlatformNotReady):
        await poe_data._async_update()

    assert poe_data.available is False


@pytest.mark.asyncio
async def test_turn_on_delegates_to_device_command(poe_data):
    """The entity must send the expected command for its port."""
    poe_data.ports = {"3": {"state": STATE_OFF}}
    poe_data.change_state = AsyncMock(return_value=True)
    entity = ZyxelPoeSwitch(poe_data, "192.0.2.10", "3")

    await entity.async_turn_on()

    poe_data.change_state.assert_awaited_once_with("3", 1)
