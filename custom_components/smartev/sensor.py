# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

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
            SmartEVPeriodConsumptionSensor(
                coordinator,
                flat_id,
                "current_year_consumption",
                "currentYearConsumption",
            ),
            SmartEVPeriodConsumptionSensor(
                coordinator,
                flat_id,
                "current_month_consumption",
                "currentMonthConsumption",
            ),
            SmartEVPeriodConsumptionSensor(
                coordinator,
                flat_id,
                "today_consumption",
                "todayConsumption",
            ),
            SmartEVPeriodProductionSensor(
                coordinator,
                flat_id,
                "current_month_production",
                "currentMonthProduction",
            ),
            SmartEVLatestDailyProductionSensor(coordinator, flat_id),
            SmartEVEstimatedDailyProductionSensor(coordinator, flat_id),
            SmartEVEstimatedProductionTotalSensor(coordinator, flat_id),
            SmartEVPeriodGridEnergySensor(
                coordinator,
                flat_id,
                "current_month_grid_energy",
                "currentMonthGridEnergy",
            ),
            SmartEVPeriodGridEnergySensor(
                coordinator,
                flat_id,
                "today_grid_energy",
                "todayGridEnergy",
            ),
            SmartEVTotalGridEnergySensor(coordinator, flat_id),
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


class SmartEVPeriodConsumptionSensor(SmartEVBaseSensor):
    """SmartEV server-provided period consumption."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:lightning-bolt"

    def __init__(
        self,
        coordinator: SmartEVCoordinator,
        flat_id: int,
        translation_key: str,
        data_key: str,
    ) -> None:
        super().__init__(coordinator, flat_id)
        self._attr_translation_key = translation_key
        self._data_key = data_key
        self._attr_unique_id = f"meter_{self._meter_id}_{translation_key}"

    @property
    def available(self) -> bool:
        """Return whether the API provided this period's consumption."""
        return super().available and self.native_value is not None

    @property
    def native_value(self) -> int | float | None:
        """Return the server-provided consumption value."""
        if not self.coordinator.data:
            return None

        return self.coordinator.data.get(self._data_key)


class SmartEVPeriodProductionSensor(SmartEVPeriodConsumptionSensor):
    """SmartEV server-provided period PV production."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:solar-power"


class SmartEVLatestDailyProductionSensor(SmartEVPeriodProductionSensor):
    """Latest daily PV production published by SmartEV."""

    # A completed day's record is neither a cumulative total nor a current
    # measurement. Override the production sensor's inherited state class.
    _attr_state_class = None

    def __init__(self, coordinator: SmartEVCoordinator, flat_id: int) -> None:
        super().__init__(
            coordinator,
            flat_id,
            "latest_daily_production",
            "latestDailyProduction",
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the date to which the delayed production value applies."""
        production_date = self.coordinator.data.get("latestDailyProductionDate")
        return {"production_date": production_date} if production_date else {}


class SmartEVEstimatedDailyProductionSensor(SmartEVPeriodProductionSensor):
    """Today's apartment PV production estimated from the live JOM meter."""

    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator: SmartEVCoordinator, flat_id: int) -> None:
        super().__init__(
            coordinator,
            flat_id,
            "estimated_pv_production",
            "estimated_today",
        )
        self._attr_unique_id = (
            f"meter_{self._meter_id}_estimated_pv_production"
        )

    @property
    def available(self) -> bool:
        """Return whether today's allocation estimate is current."""
        allocation = self.coordinator.data.get("pvAllocation") or {}
        return super().available and bool(allocation.get("today_available"))

    @property
    def native_value(self) -> int | float | None:
        """Return today's estimated apartment PV production."""
        allocation = self.coordinator.data.get("pvAllocation") or {}
        return allocation.get(self._data_key)

    @property
    def extra_state_attributes(self) -> dict:
        """Expose calibration diagnostics."""
        allocation = self.coordinator.data.get("pvAllocation") or {}
        return {
            key: allocation.get(key)
            for key in (
                "allocation_coefficient",
                "sample_days",
                "used_calibration_samples",
                "skipped_zero_grid_samples",
                "last_calibration",
                "calibration_stable",
                "minimum_coefficient",
                "maximum_coefficient",
                "standard_deviation",
                "coefficient_of_variation",
            )
            if allocation.get(key) is not None
        }


class SmartEVEstimatedProductionTotalSensor(SmartEVEstimatedDailyProductionSensor):
    """Monotonic apartment PV estimate for the Energy Dashboard."""

    _attr_translation_key = "estimated_pv_energy_total"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:solar-power-variant"

    def __init__(self, coordinator: SmartEVCoordinator, flat_id: int) -> None:
        super().__init__(coordinator, flat_id)
        self._data_key = "estimated_total"
        self._attr_translation_key = "estimated_pv_energy_total"
        self._attr_unique_id = f"meter_{self._meter_id}_estimated_pv_energy_total"

    @property
    def available(self) -> bool:
        """Return whether a valid cumulative allocation estimate exists."""
        allocation = self.coordinator.data.get("pvAllocation") or {}
        return (
            SmartEVPeriodConsumptionSensor.available.fget(self)
            and bool(allocation.get("available"))
        )

class SmartEVPeriodGridEnergySensor(SmartEVPeriodConsumptionSensor):
    """Authoritative completed grid energy plus the current live estimate."""

    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:transmission-tower"

    @property
    def extra_state_attributes(self) -> dict:
        """Expose the source and latest authoritative reconciliation."""
        accounting = self.coordinator.data.get("gridAccounting") or {}
        return {
            key: accounting.get(key)
            for key in (
                "today_source",
                "last_official_date",
                "last_reconciliation",
            )
            if accounting.get(key) is not None
        }


class SmartEVTotalGridEnergySensor(SmartEVBaseSensor):
    """Cumulative public-grid import for the Energy Dashboard."""

    _attr_translation_key = "total_grid_energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:transmission-tower-import"

    def __init__(self, coordinator: SmartEVCoordinator, flat_id: int) -> None:
        super().__init__(coordinator, flat_id)
        self._attr_unique_id = f"meter_{self._meter_id}_total_grid_energy"

    @property
    def available(self) -> bool:
        """Return whether both cumulative inputs are available."""
        cumulative = self.coordinator.data.get("gridCumulative") or {}
        return super().available and bool(cumulative.get("available"))

    @property
    def native_value(self) -> int | float | None:
        """Return cumulative imported grid energy."""
        cumulative = self.coordinator.data.get("gridCumulative") or {}
        return cumulative.get("total")

    @property
    def extra_state_attributes(self) -> dict:
        """Expose authoritative-accounting and continuity diagnostics."""
        cumulative = self.coordinator.data.get("gridCumulative") or {}
        return {
            key: cumulative.get(key)
            for key in (
                "today_source",
                "last_official_date",
                "migration_baseline_offset",
                "migration_reference_total",
                "continuity_offset",
                "last_reconciliation",
                "official_completed_total",
                "today_estimate",
            )
            if cumulative.get(key) is not None
        }


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
