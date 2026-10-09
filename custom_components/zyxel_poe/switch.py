from datetime import timedelta
import logging
import asyncio
import aiohttp
import async_timeout
import math
from random import random

from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.util import Throttle
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.exceptions import PlatformNotReady
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)


def encode(_input):
    password = ""
    possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    _len = lenn = len(_input)
    i = 1
    while i <= (321 - _len):
        if 0 == i % 5 and _len > 0:
            _len -= 1
            password += _input[_len]
        elif i == 123:
            password += "0" if lenn < 10 else str(math.floor(lenn / 10))
        elif i == 289:
            password += str(lenn % 10)
        else:
            password += possible[math.floor(random() * len(possible))]
        i += 1
    return password


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    host = config_entry.data[CONF_HOST]
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]

    session = async_create_clientsession(
        hass, cookie_jar=aiohttp.CookieJar(unsafe=True)
    )
    poe_data = ZyxelPoeData(hass, host, username, password, SCAN_INTERVAL, session)

    await poe_data.async_update()

    switches = [
        ZyxelPoeSwitch(poe_data, host, port)
        for port in poe_data.ports
    ]
    async_add_entities(switches, False)


class ZyxelPoeSwitch(SwitchEntity):
    """Representation of a ZyXEL PoE switch."""

    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_has_entity_name = True

    def __init__(self, poe_data, host, port):
        self._poe_data = poe_data
        self._host = host
        self._port = port
        self._attr_unique_id = f"{host}_port_{port}"

    @property
    def device_info(self):
        return self._poe_data.device_info

    @property
    def is_on(self):
        return self._poe_data.ports[self._port]["state"] == STATE_ON

    async def async_turn_on(self):
        self._poe_data.ports[self._port]["state"] = STATE_ON
        return await self._poe_data.change_state(self._port, 1)

    async def async_turn_off(self):
        self._poe_data.ports[self._port]["state"] = STATE_OFF
        return await self._poe_data.change_state(self._port, 0)

    @property
    def name(self):
        return f"Port {self._port}"

    @property
    def extra_state_attributes(self):
        return self._poe_data.ports[self._port]

    async def async_update(self):
        await self._poe_data.async_update()


class ZyxelPoeData:
    def __init__(self, hass, host, username, password, interval, session):
        self._hass = hass
        self._host = host
        self.devices = {}
        self.ports = {}
        self._url = f"http://{host}/cgi-bin/dispatcher.cgi"
        self._username = username
        self._password = password
        self._session = session
        self.device_info = {
            "identifiers": {("zyxel_poe", host)},
            "name": host,
            "manufacturer": "Zyxel",
            "configuration_url": f"http://{host}",
        }
        self._device_info_loaded = False
        self.async_update = Throttle(interval)(self._async_update)

    async def _login(self, is_retry=False):
        if "HTTP_XSSID" in [c.key for c in self._session.cookie_jar]:
            return

        login_data = {
            "username": self._username,
            "password": encode(self._password),
            "login": "true;",
        }

        login_step1 = await self._session.post(self._url, data=login_data)
        auth_id = (await login_step1.text()).strip()

        login_check_data = {"authId": auth_id, "login_chk": "true"}
        await asyncio.sleep(1)

        login_step2 = await self._session.post(
            self._url, data=login_check_data
        )
        text = await login_step2.text()

        if "OK" not in text:
            if is_retry:
                raise Exception(f"Login failed: {text}")
            await self._login(is_retry=True)

    async def change_state(self, port, state, is_retry=False):
        from bs4 import BeautifulSoup

        try:
            with async_timeout.timeout(10):
                await self._login()
                ret = await self._session.get(self._url, params={"cmd": "773"})
                text = await ret.text()

                if not ret.ok:
                    raise PlatformNotReady(
                        f"Refresh failed. Got response: {text}"
                    )

                soup = BeautifulSoup(text, "html.parser")
                xssid_content = soup.find(
                    "input", {"name": "XSSID"}
                ).get("value")
        except (asyncio.TimeoutError, aiohttp.ClientError) as ex:
            raise PlatformNotReady(
                f"Connection error while connecting to {self._url}: {ex}"
            ) from ex

        command_data = {
            "XSSID": xssid_content,
            "portlist": port,
            "state": state,
            "portPriority": 2,
            "portPowerMode": 3,
            "portRangeDetection": 0,
            "portLimitMode": 0,
            "poeTimeRange": 20,
            "cmd": 775,
            "sysSubmit": "Apply",
        }

        try:
            with async_timeout.timeout(10):
                await self._login()
                res = await self._session.post(self._url, data=command_data)
                text = await res.text()

                if "window.location.replace" not in text:
                    if is_retry:
                        _LOGGER.error("Cannot perform action: %s", text)
                        return False
                    self._session.cookie_jar.clear()
                    await self._login(is_retry=True)
                    return await self.change_state(port, state, is_retry=True)
        except (asyncio.TimeoutError, aiohttp.ClientError) as ex:
            raise PlatformNotReady(
                f"Connection error while connecting to {self._url}: {ex}"
            ) from ex

        return True


    async def _async_update_device_info(self):
        """Read switch identity and update the Home Assistant device registry."""
        from bs4 import BeautifulSoup

        try:
            with async_timeout.timeout(10):
                # The switch may have expired its web session since the last
                # port poll. Authenticate before requesting the status page.
                await self._login()
                ret = await self._session.get(self._url, params={"cmd": "12"})
                page = await ret.text()

                if not ret.ok:
                    _LOGGER.warning(
                        "Cannot retrieve device information from %s (HTTP %s)",
                        self._url,
                        ret.status,
                    )
                    return

                soup = BeautifulSoup(page, "html.parser")

                # Some firmware responds with a login page (without any table
                # rows) when the session cookie has expired. Re-authenticate
                # once and retry before treating the page as unparsable.
                if not soup.find("tr"):
                    _LOGGER.debug(
                        "Zyxel status page from %s contained no table rows "
                        "(HTTP %s, URL %s, content type %s); retrying after login",
                        self._url,
                        ret.status,
                        ret.url,
                        ret.headers.get("Content-Type", "unknown"),
                    )
                    self._session.cookie_jar.clear()
                    await self._login(is_retry=True)
                    ret = await self._session.get(self._url, params={"cmd": "12"})
                    page = await ret.text()
                    if not ret.ok:
                        _LOGGER.warning(
                            "Cannot retrieve device information from %s after "
                            "re-authentication (HTTP %s)",
                            self._url,
                            ret.status,
                        )
                        return
                    soup = BeautifulSoup(page, "html.parser")

                labels = {
                    "system name": "name",
                    "model name": "model",
                    "revision": "hw_version",
                    "hardware revision": "hw_version",
                    "serial number": "serial_number",
                    "firmware version": "sw_version",
                }
                details = {}

                # Zyxel firmware versions may use either td or th cells.
                for row in soup.find_all("tr"):
                    cells = row.find_all(["td", "th"], recursive=False)
                    if len(cells) < 2:
                        continue

                    for index, cell in enumerate(cells[:-1]):
                        label = " ".join(
                            cell.get_text(" ", strip=True).lower().rstrip(":").split()
                        )
                        field = labels.get(label)
                        if not field:
                            continue

                        value = " ".join(
                            part.get_text(" ", strip=True)
                            for part in cells[index + 1:]
                        ).strip()
                        if field == "sw_version":
                            value = value.split("|", 1)[0].strip()
                        if value:
                            details[field] = value
                        break

                if not details:
                    row_text = [
                        " ".join(row.get_text(" ", strip=True).split())
                        for row in soup.find_all("tr")
                    ]
                    _LOGGER.warning(
                        "No device information fields parsed from %s; "
                        "check the switch status-page HTML (cmd=12)",
                        self._url,
                    )
                    _LOGGER.debug("Zyxel status-page table rows: %s", row_text)
                    return

                self.device_info.update(details)

                # Existing registry entries need an explicit update: changing
                # the entity's device_info property alone is not sufficient.
                registry = dr.async_get(self._hass)
                device = registry.async_get_device(
                    identifiers={("zyxel_poe", self._host)}, connections=set()
                )
                if device is not None:
                    registry_details = {
                        key: value for key, value in details.items()
                        if key != "name"
                    }
                    if registry_details:
                        registry.async_update_device(device.id, **registry_details)

                required_fields = {"model", "hw_version", "sw_version", "serial_number"}
                self._device_info_loaded = required_fields.issubset(details)
                missing = sorted(required_fields - set(details))
                if missing:
                    _LOGGER.debug(
                        "Device information from %s is incomplete; missing fields: %s",
                        self._url,
                        ", ".join(missing),
                    )
                _LOGGER.debug(
                    "Parsed Zyxel device information from %s: %s",
                    self._url,
                    details,
                )

        except (asyncio.TimeoutError, aiohttp.ClientError) as ex:
            _LOGGER.warning(
                "Error retrieving device information from %s: %s", self._url, ex
            )

    async def _async_update(self):
        from bs4 import BeautifulSoup

        try:
            with async_timeout.timeout(10):
                await self._login()

                ret = await self._session.get(
                    self._url, params={"cmd": "773"}
                )
                text = await ret.text()

                if not ret.ok:
                    raise PlatformNotReady(
                        f"Refresh failed. Got response: {text}"
                    )

                soup = BeautifulSoup(text, "html.parser")
                table = soup.select("table")[2]

                for row in table.find_all("tr"):
                    cols = row.find_all("td")

                    if len(cols) == 13:
                        (
                            _,
                            _,
                            port,
                            state,
                            pd_class,
                            pd_priority,
                            power_up,
                            wide_range_detection,
                            consuming_power_mw,
                            max_power_mw,
                            time_range_name,
                            time_range_status,
                            _,
                        ) = map(lambda a: a.text.strip(), cols)
                    elif len(cols) == 12:
                        (
                            _,
                            _,
                            port,
                            state,
                            pd_class,
                            pd_priority,
                            power_up,
                            consuming_power_mw,
                            max_power_mw,
                            time_range_name,
                            time_range_status,
                            _,
                        ) = map(lambda a: a.text.strip(), cols)
                        wide_range_detection = "Unavailable"
                    else:
                        continue

                    if state == "Enable":
                        state = STATE_ON
                    elif state == "Disable":
                        state = STATE_OFF

                    self.ports[port] = {
                        "port": port,
                        "state": state,
                        "class": pd_class,
                        "priority": pd_priority,
                        "power_up": power_up,
                        "wide_range_detection": wide_range_detection,
                        "current_power_w": int(consuming_power_mw) / 1000.0,
                        "max_power_w": int(max_power_mw) / 1000.0,
                        "time_range_name": time_range_name,
                        "time_range_status": time_range_status,
                    }

        except (asyncio.TimeoutError, aiohttp.ClientError) as ex:
            raise PlatformNotReady(
                f"Connection error while connecting to {self._url}: {ex}"
            ) from ex

        if not self._device_info_loaded:
            await self._async_update_device_info()
