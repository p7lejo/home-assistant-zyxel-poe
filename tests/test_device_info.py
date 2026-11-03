"""Tests for switch identity and uptime parsing."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest


def _status_html(uptime="0 days, 6 hours, 10 mins, 27 secs"):
    """Build a representative cmd=12 status page."""
    rows = {
        "System Name": "GS1900",
        "Model Name": "GS1900-8HP",
        "Hardware Revision": "B2",
        "Serial Number": "S123456789",
        "Firmware Version": "V2.90(AAHI.2) | 05/07/2026",
        "System Up Time": uptime,
    }
    table_rows = "".join(
        f"<tr><td>{label}</td><td>{value}</td></tr>"
        for label, value in rows.items()
    )
    return f"<html><table>{table_rows}</table></html>"


@pytest.mark.asyncio
async def test_device_info_parser_reads_model_firmware_and_serial(poe_data):
    """The status page fills the device registry metadata fields."""
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = _status_html()
    poe_data._session.get = AsyncMock(return_value=response)

    await poe_data._async_update_device_info()

    assert poe_data.device_info["name"] == "GS1900"
    assert poe_data.device_info["model"] == "GS1900-8HP"
    assert poe_data.device_info["hw_version"] == "B2"
    assert poe_data.device_info["serial_number"] == "S123456789"
    assert poe_data.device_info["sw_version"] == "V2.90(AAHI.2)"
    assert poe_data._device_info_loaded is True


@pytest.mark.asyncio
async def test_partial_device_info_does_not_mark_metadata_complete(poe_data):
    """Missing required identity fields leave metadata eligible for later refresh."""
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = (
        "<table><tr><td>System Name</td><td>GS1900</td></tr></table>"
    )
    poe_data._session.get = AsyncMock(return_value=response)

    await poe_data._async_update_device_info()

    assert poe_data.device_info["name"] == "GS1900"
    assert poe_data._device_info_loaded is False


@pytest.mark.asyncio
async def test_system_start_requires_two_matching_candidates_after_reboot(
    poe_data, monkeypatch
):
    """A changed boot timestamp is accepted only after a second matching sample."""
    from custom_components.zyxel_poe import switch as switch_module

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 15, 12, 0, 30, tzinfo=tz or timezone.utc)

    monkeypatch.setattr(switch_module, "datetime", FrozenDateTime)
    poe_data.system_start = datetime(2026, 10, 15, 11, 40, tzinfo=timezone.utc)
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = _status_html()
    poe_data._session.get = AsyncMock(return_value=response)

    await poe_data._async_update_device_info()
    first_candidate = poe_data._pending_system_start

    assert first_candidate is not None
    assert poe_data.system_start == datetime(
        2026, 10, 15, 11, 40, tzinfo=timezone.utc
    )
    assert poe_data._pending_system_start_count == 1

    await poe_data._async_update_device_info()

    assert poe_data.system_start == first_candidate
    assert poe_data._pending_system_start is None
    assert poe_data._pending_system_start_count == 0


@pytest.mark.asyncio
async def test_system_start_ignores_changes_of_two_minutes_or_less(
    poe_data, monkeypatch
):
    """Small inferred timestamp changes are treated as request-time jitter."""
    from custom_components.zyxel_poe import switch as switch_module

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 15, 12, 0, 30, tzinfo=tz or timezone.utc)

    monkeypatch.setattr(switch_module, "datetime", FrozenDateTime)
    poe_data.system_start = datetime(2026, 10, 15, 11, 51, tzinfo=timezone.utc)
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = True
    response.text.return_value = _status_html()
    poe_data._session.get = AsyncMock(return_value=response)

    await poe_data._async_update_device_info()

    assert poe_data.system_start == datetime(
        2026, 10, 15, 11, 51, tzinfo=timezone.utc
    )
    assert poe_data._pending_system_start is None


@pytest.mark.asyncio
async def test_device_info_http_error_does_not_mark_metadata_loaded(poe_data):
    """An HTTP error is handled without publishing incomplete metadata."""
    poe_data._login = AsyncMock()
    response = AsyncMock()
    response.ok = False
    response.status = 500
    response.text.return_value = "Internal Server Error"
    poe_data._session.get = AsyncMock(return_value=response)

    await poe_data._async_update_device_info()

    assert poe_data._device_info_loaded is False
