"""Heating and domestic hot water temperature settings."""

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError

from .entity import BoilerEntity
from .protocol import TARGETS


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(BoilerSetpoint(entry, field) for field in TARGETS)


class BoilerSetpoint(BoilerEntity, NumberEntity):
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, entry, field: str) -> None:
        super().__init__(entry, field)
        _, self._attr_native_min_value, self._attr_native_max_value = TARGETS[field]

    @property
    def native_value(self) -> int:
        return self.value

    async def async_set_native_value(self, value: float) -> None:
        if not self._attr_native_min_value <= value <= self._attr_native_max_value:
            raise HomeAssistantError("Temperature is outside the supported range")
        await self.coordinator.async_set(self.field, round(value))
