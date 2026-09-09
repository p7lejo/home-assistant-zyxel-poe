[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

Manage the Power-over-Ethernet functionality of ZyXEL switches.
Because this functionality is not available via SNMP (WTF, ZyXEL?) it will be performed over HTTP. Admin credentials are required.

# Compatibility

## Home Assistant

Requires Home Assistant 2023.1.0 or newer.

## Tested Devices

Tested with:

- ZyXEL GS1900-8HP
- ZyXEL GS1900-10HP
- ZyXEL GS1900-24EP

Should be compatible with similar models.

## Installation

### Method 1: HACS (Recommended)

This integration is available in HACS (Home Assistant Community Store). Search for "ZyXEL PoE" in HACS and install it directly.

## Configuration

### Home Assistant UI

This integration supports configuration through the Home Assistant UI:

1. Go to **Settings** → **Devices & Services**
2. Click the **+ ADD INTEGRATION** button
3. Search for "ZyXEL PoE" and select it
4. Follow the configuration steps to add your ZyXEL switch

After the switch has been added, each physical PoE port is automatically created as an entity associated with the switch device. The ports are represented as **virtual switches** and can be controlled manually from Home Assistant just like a smart plug: turning a port on or off enables or disables PoE power on the corresponding physical port.

The port entities can be renamed in Home Assistant to match the connected device, for example "Terrace Camera" or "Access Point". This makes it easy to identify and control individual PoE-connected devices directly from Home Assistant.

In addition to controlling the PoE ports, the integration provides the **current power consumption of each port** as a Home Assistant sensor. The power consumption is read from the switch and displayed in watts, allowing it to be used in dashboards, automations, and statistics.

These enhancements build on the functionality of the original fork, which already provided individual PoE port control. The current version extends this by integrating the ports more naturally into Home Assistant, including user-configurable entity names and dedicated power-consumption sensors.

### Method 2: Manual Installation

To install manually, copy the `zyxel_poe` folder into your [custom_components folder](https://developers.home-assistant.io/docs/en/creating_component_loading.html).

## Configuration

```yaml
# Example configuration.yaml entry
switch:
- platform: zyxel_poe
  devices:
  - host: switch1.local
    username: admin
    password: !secret switch1
  - host: switch2.local
    username: admin
    password: !secret switch2
```
