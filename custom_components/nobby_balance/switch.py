"""Boiler power and central heating switches."""

from homeassistant.components.switch import SwitchEntity

from .entity import BoilerEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(BoilerSwitch(entry, field) for field in ("power", "heating"))


class BoilerSwitch(BoilerEntity, SwitchEntity):
    @property
    def is_on(self) -> bool:
        return self.value

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set(self.field, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set(self.field, False)
