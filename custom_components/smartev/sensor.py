"""SmartEV sensor platform."""

from datetime import UTC, datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FLAT_ID, DOMAIN
from .coordinator import SmartEVCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SmartEV sensors."""

    coordinator = entry.runtime_data
    flat_id = entry.data[CONF_FLAT_ID]

    async_add_entities(
        [
            SmartEVMeterSensor(coordinator, flat_id),
            SmartEVLastReadingSensor(coordinator, flat_id),
        ]
    )


class SmartEVBaseSensor(CoordinatorEntity, SensorEntity):
    """Base SmartEV sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SmartEVCoordinator,
        flat_id: int,
    ) -> None:
        """Initialize sensor."""

        super().__init__(coordinator)

        meter = coordinator.data["meters"][0]
        meter_id = meter["id"]

        self._meter_id = meter_id

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"meter_{meter_id}")},
            manufacturer="SmartEV",
            model="Elektroměr",
            name=f"{coordinator.data['buildingName']} - byt {coordinator.data['number']}",
        )

    @property
    def meter(self) -> dict | None:
        """Return first meter."""

        data = self.coordinator.data

        if not data:
            return None

        meters = data.get("meters")

        if not meters:
            return None

        return meters[0]


class SmartEVMeterSensor(SmartEVBaseSensor):
    """SmartEV total energy."""

    _attr_translation_key = "total_energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator: SmartEVCoordinator, flat_id: int) -> None:
        super().__init__(coordinator, flat_id)
        self._attr_unique_id = f"meter_{self._meter_id}_energy"

    @property
    def native_value(self):
        """Return total energy."""

        meter = self.meter

        if meter is None:
            return None

        return meter.get("value1")


class SmartEVLastReadingSensor(SmartEVBaseSensor):
    """SmartEV last reading."""

    _attr_translation_key = "last_reading"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: SmartEVCoordinator, flat_id: int) -> None:
        super().__init__(coordinator, flat_id)
        self._attr_unique_id = f"meter_{self._meter_id}_last_reading"

    @property
    def native_value(self):
        """Return timestamp of last meter reading."""

        meter = self.meter

        if meter is None:
            return None

        timestamp = meter.get("dt")

        if timestamp is None:
            return None

        return datetime.fromtimestamp(timestamp, UTC)