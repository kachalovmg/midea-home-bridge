"""Boiler telemetry."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfPressure, UnitOfTemperature

from .entity import BoilerEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([
        BoilerMeasurement(entry, "heating_temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
        BoilerMeasurement(entry, "water_temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
        BoilerMeasurement(entry, "pressure", SensorDeviceClass.PRESSURE, UnitOfPressure.BAR),
        BoilerMode(entry, "mode"),
        BoilerError(entry, "error_code"),
    ])


class BoilerSensor(BoilerEntity, SensorEntity):
    @property
    def native_value(self):
        return self.value


class BoilerMeasurement(BoilerSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry, field, device_class, unit) -> None:
        super().__init__(entry, field)
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit


class BoilerMode(BoilerSensor):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["idle", "heating", "hot_water"]


class BoilerError(BoilerSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
