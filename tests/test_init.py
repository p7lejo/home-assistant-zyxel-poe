"""Tests for integration setup and unload."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.zyxel_poe import PLATFORMS, async_setup_entry, async_unload_entry


@pytest.mark.asyncio
async def test_setup_forwards_both_platforms(hass):
    """Setup forwards switch and sensor platforms."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain="zyxel_poe",
        title="ZyXEL PoE",
        data={"host": "192.0.2.10", "username": "admin", "password": "secret"},
        source="user",
        entry_id="test-entry",
        options={},
    )
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    assert await async_setup_entry(hass, entry) is True
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, PLATFORMS
    )
    assert hass.data["zyxel_poe"]["test-entry"] == entry.data


@pytest.mark.asyncio
async def test_unload_removes_entry_data(hass):
    """Successful platform unload removes entry runtime data."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain="zyxel_poe",
        title="ZyXEL PoE",
        data={"host": "192.0.2.10", "username": "admin", "password": "secret"},
        source="user",
        entry_id="test-entry",
        options={},
    )
    hass.data.setdefault("zyxel_poe", {})["test-entry"] = entry.data
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    assert await async_unload_entry(hass, entry) is True
    assert "test-entry" not in hass.data["zyxel_poe"]
