"""Tests for integration setup and unload."""

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zyxel_poe import PLATFORMS, async_setup_entry, async_unload_entry


@pytest.mark.asyncio
async def test_setup_forwards_both_platforms(hass, monkeypatch):
    """Setup forwards switch and sensor platforms."""
    entry = MockConfigEntry(
        domain="zyxel_poe",
        title="ZyXEL PoE",
        data={"host": "192.0.2.10", "username": "admin", "password": "secret"},
    )
    forward = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", forward)

    assert await async_setup_entry(hass, entry) is True
    forward.assert_awaited_once_with(entry, PLATFORMS)
    assert hass.data["zyxel_poe"][entry.entry_id] == entry.data


@pytest.mark.asyncio
async def test_unload_removes_entry_data(hass, monkeypatch):
    """Successful platform unload removes entry runtime data."""
    entry = MockConfigEntry(
        domain="zyxel_poe",
        title="ZyXEL PoE",
        data={"host": "192.0.2.10", "username": "admin", "password": "secret"},
    )
    entry.add_to_hass(hass)
    hass.data.setdefault("zyxel_poe", {})[entry.entry_id] = entry.data
    unload = AsyncMock(return_value=True)
    monkeypatch.setattr(hass.config_entries, "async_unload_platforms", unload)

    assert await async_unload_entry(hass, entry) is True
    assert entry.entry_id not in hass.data["zyxel_poe"]
