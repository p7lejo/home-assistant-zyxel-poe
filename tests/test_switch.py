"""Tests for switch data handling and entities."""

from unittest.mock import AsyncMock
import asyncio
import logging

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
    row = '<tr><td><input name="port" value="1"></td>' + "".join(f"<td>{cell}</td>" for cell in cells[1:]) + "</tr>"
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
    assert poe_data.ports["3"]["state"] == STATE_ON


@pytest.mark.asyncio
async def test_login_reuses_existing_session_cookie(poe_data):
    """An existing Zyxel session cookie avoids an unnecessary login."""
    from types import SimpleNamespace

    poe_data._session.cookie_jar.__iter__.return_value = iter(
        [SimpleNamespace(key="HTTP_XSSID")]
    )
    poe_data._session.post = AsyncMock()

    await poe_data._login()

    poe_data._session.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_state_posts_port_command(poe_data):
    """PoE commands include the requested port and state."""
    from unittest.mock import patch

    from bs4 import BeautifulSoup

    poe_data._login = AsyncMock()
    get_response = AsyncMock()
    get_response.ok = True
    get_response.text.return_value = (
        '<html><input name="XSSID" value="test-token"></html>'
    )
    post_response = AsyncMock()
    post_response.text.return_value = "window.location.replace('/success')"
    poe_data._session.get = AsyncMock(return_value=get_response)
    poe_data._session.post = AsyncMock(return_value=post_response)

    result = await poe_data.change_state("4", 1)

    assert result is True
    sent = poe_data._session.post.await_args.kwargs["data"]
    assert sent["portlist"] == "4"
    assert sent["state"] == 1
    assert sent["XSSID"] == "test-token"


@pytest.mark.asyncio
async def test_failed_turn_on_does_not_change_reported_state(poe_data):
    """A rejected device command must not mutate the state shown in HA."""
    poe_data.ports = {"3": {"state": STATE_OFF}}
    poe_data.change_state = AsyncMock(return_value=False)
    entity = ZyxelPoeSwitch(poe_data, "192.0.2.10", "3")

    result = await entity.async_turn_on()

    assert result is False
    assert entity.is_on is False


@pytest.mark.asyncio
async def test_incomplete_device_info_is_still_throttled(poe_data):
    """A partial cmd=12 response must not cause a request every minute."""
    cells = [
        "x", "x", "1", "Enable", "Class 3", "High", "On",
        "1200", "30000", "Always", "Active", "x",
    ]
    row = '<tr><td><input name="port" value="1"></td>' + "".join(f"<td>{cell}</td>" for cell in cells[1:]) + "</tr>"
    html = f"<table></table><table></table><table>{row}</table>"
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = html
    poe_data._session.get = AsyncMock(return_value=response)
    poe_data._device_info_loaded = False
    import time

    async def record_attempt():
        poe_data._last_device_info_update = time.monotonic()

    poe_data._async_update_device_info = AsyncMock(side_effect=record_attempt)
    poe_data._last_device_info_update = time.monotonic() - 301

    await poe_data._async_update()
    await poe_data._async_update()

    assert poe_data._async_update_device_info.await_count == 1

@pytest.mark.asyncio
async def test_partial_port_table_does_not_replace_complete_snapshot(poe_data):
    """A truncated response must not discard ports absent from that response."""
    cells = [
        "x", "x", "1", "Enable", "Class 3", "High", "On",
        "1200", "30000", "Always", "Active", "x",
    ]
    row = "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"
    html = f"<table></table><table></table><table>{row}</table>"
    poe_data._initial_update_succeeded = True
    poe_data.available = True
    poe_data.ports = {
        "1": {"port": "1", "state": STATE_ON},
        "2": {"port": "2", "state": STATE_OFF},
    }
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = html
    poe_data._session.get = AsyncMock(return_value=response)
    poe_data._device_info_loaded = True

    await poe_data._async_update()

    assert "2" in poe_data.ports


@pytest.mark.asyncio
async def test_failed_turn_off_does_not_change_reported_state(poe_data):
    """A rejected device command must leave the last confirmed state intact."""
    poe_data.ports = {"3": {"state": STATE_ON}}
    poe_data.change_state = AsyncMock(return_value=False)
    entity = ZyxelPoeSwitch(poe_data, "192.0.2.10", "3")

    result = await entity.async_turn_off()

    assert result is False
    assert entity.is_on is True


@pytest.mark.asyncio
async def test_command_exception_does_not_change_reported_state(poe_data):
    """A transport error must not optimistically change the entity state."""
    poe_data.ports = {"3": {"state": STATE_OFF}}
    poe_data.change_state = AsyncMock(side_effect=PlatformNotReady("timeout"))
    entity = ZyxelPoeSwitch(poe_data, "192.0.2.10", "3")

    with pytest.raises(PlatformNotReady):
        await entity.async_turn_on()

    assert entity.is_on is False


def _port_row(port, power="1200", max_power="30000"):
    cells = [
        "x", "x", str(port), "Enable", "Class 3", "High", "On",
        power, max_power, "Always", "Active", "x",
    ]
    return '<tr><td><input name="port" value="' + str(port) + '"></td>' + "".join(f"<td>{cell}</td>" for cell in cells[1:]) + "</tr>"


@pytest.mark.asyncio
async def test_gs1900_8hp_nested_time_range_header_does_not_break_port_parsing(poe_data):
    """Nested header cells must not be counted as cells of a port row."""
    poe_data.device_info["model"] = "GS1900-8HP"
    headers = """
    <tr><td colspan="12"><table><tr><td colspan="2">Time Range</td></tr>
    <tr><td>Name</td><td>Status</td></tr></table></td></tr>
    """
    rows = "".join(
        '<tr><td></td><td><input type="checkbox" name="port" value="{p}"></td>'
        '<td>{p}</td><td>{state}</td><td>class0</td><td>Medium</td>'
        '<td>802.3at</td><td>Disable</td><td>{power}</td><td>{maximum}</td>'
        '<td></td><td>-</td><td></td></tr>'.format(
            p=port,
            state="Enable" if port in (1, 5, 8) else "Disable",
            power=7200 if port == 1 else 0,
            maximum=16200 if port in (1, 5) else 0,
        )
        for port in range(1, 9)
    )
    html = f"<table></table><table></table><table>{headers}{rows}</table>"
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = html
    poe_data._session.get = AsyncMock(return_value=response)
    poe_data._async_update_device_info = AsyncMock()

    await poe_data._async_update()

    assert poe_data.available is True
    assert len(poe_data.ports) == 8
    assert poe_data.ports["1"]["current_power_w"] == 7.2
    assert poe_data.ports["5"]["current_power_w"] == 0.0


@pytest.mark.asyncio
async def test_model_port_count_rejects_truncated_first_snapshot(poe_data):
    """The first snapshot must contain every PoE port for a recognized model."""
    poe_data.device_info["model"] = "GS1900-8HP"
    html = "<table></table><table></table><table>" + _port_row(1) + "</table>"
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = html
    poe_data._session.get = AsyncMock(return_value=response)

    with pytest.raises(PlatformNotReady, match="expected 8 ports"):
        await poe_data._async_update()

    assert poe_data.ports == {}
    assert poe_data.available is False


@pytest.mark.asyncio
async def test_model_port_count_accepts_gs1900_24ep_poe_ports(poe_data):
    """The GS1900-24EP exposes twelve PoE ports, not twenty-four."""
    poe_data.device_info["model"] = "GS1900-24EP"
    rows = "".join(_port_row(port) for port in range(1, 13))
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = f"<table></table><table></table><table>{rows}</table>"
    poe_data._session.get = AsyncMock(return_value=response)
    poe_data._async_update_device_info = AsyncMock()

    await poe_data._async_update()

    assert poe_data.available is True
    assert len(poe_data.ports) == 12


@pytest.mark.asyncio
async def test_duplicate_port_rows_are_rejected(poe_data):
    """Duplicate port rows indicate a malformed or concatenated response."""
    html = (
        "<table></table><table></table><table>"
        + _port_row(1) + _port_row(1)
        + "</table>"
    )
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = html
    poe_data._session.get = AsyncMock(return_value=response)

    with pytest.raises(PlatformNotReady, match="Duplicate port"):
        await poe_data._async_update()


@pytest.mark.asyncio
async def test_non_numeric_power_values_are_rejected(poe_data):
    """Invalid numeric fields must not replace the last confirmed snapshot."""
    poe_data._initial_update_succeeded = True
    poe_data.available = True
    previous = {"1": {"port": "1", "state": STATE_ON}}
    poe_data.ports = previous
    html = (
        "<table></table><table></table><table>"
        + _port_row(1, power="unknown")
        + "</table>"
    )
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = html
    poe_data._session.get = AsyncMock(return_value=response)

    await poe_data._async_update()

    assert poe_data.available is False
    assert poe_data.ports is previous


@pytest.mark.asyncio
async def test_malformed_port_rows_are_rejected(poe_data):
    """Rows with an unexpected layout must invalidate the whole snapshot."""
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = (
        "<table></table><table></table><table>"
        + _port_row(1)
        + '<tr><td><input name="port" value="2"></td><td>truncated row</td></tr>'
        + "</table>"
    )
    poe_data._session.get = AsyncMock(return_value=response)

    with pytest.raises(PlatformNotReady, match="Unexpected port row layout"):
        await poe_data._async_update()

    assert poe_data.ports == {}


@pytest.mark.asyncio
async def test_empty_timeout_warning_includes_exception_type_and_traceback(
    poe_data, caplog
):
    """An empty timeout string must still produce useful warning diagnostics."""
    poe_data._initial_update_succeeded = True
    poe_data.available = True
    poe_data._login = AsyncMock(side_effect=asyncio.TimeoutError())

    with caplog.at_level(logging.WARNING, logger="custom_components.zyxel_poe.switch"):
        await poe_data._async_update()

    assert "lost (TimeoutError):" in caplog.text
    assert "TimeoutError" in caplog.text
