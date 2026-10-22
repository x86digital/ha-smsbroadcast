"""SMS Broadcast credit balance sensor."""

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([CreditBalance(entry.runtime_data, entry)])


class CreditBalance(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Credit balance"
    _attr_icon = "mdi:message-text"
    _attr_native_unit_of_measurement = "credits"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_balance"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": NAME,
            "manufacturer": "SMS Broadcast",
            "entry_type": DeviceEntryType.SERVICE,
        }

    @property
    def native_value(self):
        return self.coordinator.data
