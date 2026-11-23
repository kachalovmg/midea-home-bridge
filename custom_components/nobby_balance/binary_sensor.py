"""Boiler flame indication."""

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import BoilerEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([BoilerFlame(entry, "flame")])


class BoilerFlame(BoilerEntity, BinarySensorEntity):
    _attr_icon = "mdi:fire"

    @property
    def is_on(self) -> bool:
        return self.value
