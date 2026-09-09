"""The ZyXEL PoE integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SWITCH, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ZyXEL PoE from a config entry."""
    hass.data.setdefault(entry.domain, {})
    hass.data[entry.domain][entry.entry_id] = entry.data

    registry = er.async_get(hass)
    host = entry.data.get("host")
    if host:
        old_prefix = f"switch.{host}_{host}_port".replace(".", "_")
        for entity in list(registry.entities.values()):
            if (
                entity.config_entry_id == entry.entry_id
                and entity.platform == entry.domain
                and not entity.unique_id
                and entity.entity_id.startswith(old_prefix)
            ):
                registry.async_remove(entity.entity_id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[entry.domain].pop(entry.entry_id)

    return unload_ok
