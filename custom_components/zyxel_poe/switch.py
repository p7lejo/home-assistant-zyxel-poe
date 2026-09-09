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
    poe_data = ZyxelPoeData(host, username, password, SCAN_INTERVAL, session)

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
        return {
            "identifiers": {("zyxel_poe", self._host)},
            "name": self._host,
            "manufacturer": "Zyxel",
        }

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
    def __init__(self, host, username, password, interval, session):
        self.devices = {}
        self.ports = {}
        self._url = f"http://{host}/cgi-bin/dispatcher.cgi"
        self._username = username
        self._password = password
        self._session = session
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
