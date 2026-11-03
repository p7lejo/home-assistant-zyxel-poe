"""Shared fixtures for the ZyXEL PoE integration tests."""

from unittest.mock import MagicMock

import pytest

from custom_components.zyxel_poe.switch import SCAN_INTERVAL, ZyxelPoeData


@pytest.fixture
def fake_session():
    """Return a minimal aiohttp-session double."""
    session = MagicMock()
    session.cookie_jar = MagicMock()
    session.cookie_jar.__iter__.return_value = iter([])
    session.cookie_jar.clear = MagicMock()
    return session


@pytest.fixture
def poe_data(hass, fake_session):
    """Return an uninitialized switch data object."""
    return ZyxelPoeData(
        hass,
        "192.0.2.10",
        "admin",
        "secret",
        SCAN_INTERVAL,
        fake_session,
    )
