"""Sensor platform for the ZyXEL PoE integration."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .switch import SCAN_INTERVAL, ZyxelPoeData


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZyXEL PoE power sensors from a config entry."""
    host = config_entry.data[CONF_HOST]
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]

    session = async_create_clientsession(hass)
    poe_data = ZyxelPoeData(host, username, password, SCAN_INTERVAL, session)

    await poe_data.async_update()

    sensors = [
        ZyxelPoePowerSensor(poe_data, host, port)
        for port in poe_data.ports
    ]

    async_add_entities(sensors, False)


class ZyxelPoePowerSensor(SensorEntity):
    """Representation of the current PoE power consumption of a ZyXEL port."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATTS
    _attr_suggested_display_precision = 3

    def __init__(self, poe_data: ZyxelPoeData, host: str, port: str) -> None:
        self._poe_data = poe_data
        self._host = host
        self._port = port
        self._attr_unique_id = f"{host}_port_{port}_power"
        self._attr_translation_key = None

    @property
    def device_info(self):
        return {
            "identifiers": {
                ("zyxel_poe", self._host)
            },
            "name": self._host,
            "manufacturer": "Zyxel",
        }

    @property
    def name(self) -> str:
        return f"Port {self._port} consuming power"

    @property
    def native_value(self):
        return self._poe_data.ports.get(self._port, {}).get("current_power_w")

    @property
    def extra_state_attributes(self):
        port_data = self._poe_data.ports.get(self._port, {})
        return {
            "port": self._port,
            "max_power_w": port_data.get("max_power_w"),
        }

    async def async_update(self) -> None:
        await self._poe_data.async_update()
