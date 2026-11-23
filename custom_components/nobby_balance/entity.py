"""Common device identity and state lookup."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, BoilerCoordinator


class BoilerEntity(CoordinatorEntity[BoilerCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, entry, field: str) -> None:
        super().__init__(entry.runtime_data)
        self.field = field
        self._attr_translation_key = field
        self._attr_unique_id = f"{entry.entry_id}_{field}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Kentatsu",
            model="Nobby Balance",
        )

    @property
    def value(self):
        return getattr(self.coordinator.data, self.field)
