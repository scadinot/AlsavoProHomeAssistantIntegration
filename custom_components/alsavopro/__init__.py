"""Alsavo Pro pool heat pump integration."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_IP_ADDRESS,
    CONF_PORT,
    CONF_NAME,
    Platform,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .AlsavoPyCtrl import AlsavoPro
from .const import (
    DOMAIN,
    SERIAL_NO,
    UPDATE_INTERVAL,
    UPDATE_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
]


async def async_setup(hass, config):
    return True


async def async_setup_entry(hass, entry):
    """Set up the Alsavo Pro heater."""
    name = entry.data.get(CONF_NAME)
    serial_no = entry.data.get(SERIAL_NO)
    ip_address = entry.data.get(CONF_IP_ADDRESS)
    port_no = entry.data.get(CONF_PORT)
    password = entry.options.get(CONF_PASSWORD, entry.data.get(CONF_PASSWORD))

    data_handler = AlsavoPro(name, serial_no, ip_address, port_no, password)
    data_coordinator = AlsavoProDataCoordinator(hass, entry, data_handler)

    # Raises ConfigEntryNotReady if the pump can't be reached, so Home
    # Assistant retries the setup later instead of loading dead entities.
    await data_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = data_coordinator

    # Reload the entry when options (e.g. password) change so the new value is used.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_update_listener(hass, entry):
    """Reload the config entry when its options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


class AlsavoProDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config_entry, data_handler):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            # Name of the data. For logging purposes.
            name="AlsavoPro",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.data_handler = data_handler

    async def _async_update_data(self):
        try:
            async with asyncio.timeout(UPDATE_TIMEOUT):
                await self.data_handler.update()
        except TimeoutError as err:
            raise UpdateFailed(
                f"Timed out after {UPDATE_TIMEOUT} s waiting for the heat pump"
            ) from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with the heat pump: {err}") from err
        return self.data_handler


class AlsavoProEntity:
    """Mixin providing device_info for Alsavo Pro entities."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._data_handler.serial_no)},
            name=self._data_handler.name,
            manufacturer="Alsavo/Zealux",
            model="Swim&Fun 1401/1402",
            serial_number=str(self._data_handler.serial_no),
            hw_version=str(self._data_handler.get_status_value(65)),
            sw_version=str(self._data_handler.get_status_value(66)),
        )
