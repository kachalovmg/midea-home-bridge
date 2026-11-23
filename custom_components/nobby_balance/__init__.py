"""Home Assistant integration for Kentatsu Nobby Balance."""

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .protocol import BoilerClient, BoilerState, CommandUnconfirmed

DOMAIN = "nobby_balance"
PLATFORMS = (Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH)
LOGGER = logging.getLogger(__name__)


class BoilerCoordinator(DataUpdateCoordinator[BoilerState]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, LOGGER, name=DOMAIN, config_entry=entry,
            update_interval=timedelta(seconds=5), always_update=False,
        )
        self.client = BoilerClient(entry.data[CONF_HOST], entry.data[CONF_PORT])

    async def _async_update_data(self) -> BoilerState:
        try:
            return await self.client.read()
        except (TimeoutError, OSError) as err:
            raise UpdateFailed("No boiler status received from ESPHome") from err

    async def async_set(self, field: str, value: bool | int) -> None:
        try:
            state = await self.client.set(field, value)
        except CommandUnconfirmed as err:
            raise HomeAssistantError("The boiler did not confirm the setting") from err
        except OSError as err:
            raise HomeAssistantError("Communication with the ESPHome bridge failed") from err
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        self.async_set_updated_data(state)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = BoilerCoordinator(hass, entry)
    entry.runtime_data = coordinator
    try:
        await coordinator.async_config_entry_first_refresh()
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        coordinator.client.close()
        raise
    entry.async_on_unload(coordinator.client.close)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
