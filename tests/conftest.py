"""Shared fixtures for the ZyXEL PoE integration tests."""

from pathlib import Path
import sys
from unittest.mock import MagicMock

import pytest

# pytest-homeassistant-custom-component may change the import path while
# loading Home Assistant fixtures. Ensure the repository root is available
# so the integration's custom_components namespace can be imported.
REPOSITORY_ROOT = str(Path(__file__).resolve().parents[1])
if REPOSITORY_ROOT not in sys.path:
    sys.path.insert(0, REPOSITORY_ROOT)

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
