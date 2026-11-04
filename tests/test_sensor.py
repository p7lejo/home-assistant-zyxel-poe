"""Tests for the sensor platform."""

from datetime import datetime, timezone

from homeassistant.const import STATE_ON

from custom_components.zyxel_poe.sensor import (
    ZyxelPoePowerSensor,
    ZyxelPoeSystemStartSensor,
)


def test_power_sensor_value_and_attributes(poe_data):
    """Power is exposed in watts with the maximum power as an attribute."""
    poe_data.available = True
    poe_data.ports = {
        "2": {"state": STATE_ON, "current_power_w": 4.6, "max_power_w": 30.0}
    }
    sensor = ZyxelPoePowerSensor(poe_data, "192.0.2.10", "2")

    assert sensor.unique_id == "192.0.2.10_port_2_power"
    assert sensor.native_value == 4.6
    assert sensor.extra_state_attributes == {"port": "2", "max_power_w": 30.0}
    assert sensor.available is True


def test_power_sensor_unavailable_when_switch_is_unavailable(poe_data):
    """Power readings must not appear current when communication is lost."""
    poe_data.available = False
    poe_data.ports = {"2": {"current_power_w": 4.6}}
    sensor = ZyxelPoePowerSensor(poe_data, "192.0.2.10", "2")

    assert sensor.available is False


def test_system_start_sensor_exposes_timestamp(poe_data):
    """The system-start timestamp is exposed without changing its value."""
    expected = datetime(2026, 10, 15, 20, 30, tzinfo=timezone.utc)
    poe_data.available = True
    poe_data.system_start = expected
    sensor = ZyxelPoeSystemStartSensor(poe_data, "192.0.2.10")

    assert sensor.unique_id == "192.0.2.10_system_start"
    assert sensor.native_value == expected
    assert sensor.available is True


def test_system_start_sensor_is_empty_before_first_uptime_read(poe_data):
    """No timestamp is invented before uptime has been received."""
    sensor = ZyxelPoeSystemStartSensor(poe_data, "192.0.2.10")
    assert sensor.native_value is None
