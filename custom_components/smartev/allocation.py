# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

"""Automatic apartment PV allocation calibration and estimation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import math
from statistics import fmean, stdev
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    PV_ALLOCATION_HISTORY_DAYS,
    PV_ALLOCATION_MAX_COEFFICIENT_OF_VARIATION,
    PV_ALLOCATION_MAX_RELATIVE_RANGE,
    PV_ALLOCATION_MIN_JOM_PRODUCTION,
    PV_ALLOCATION_MIN_SAMPLES,
    PV_ALLOCATION_SIGNIFICANT_CHANGE,
    PV_ALLOCATION_ZERO_GRID_IMPORT,
)
from .cumulative import (
    DailyCumulativeEnergyCounter,
    DifferenceCumulativeEnergyCounter,
)

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1
_SAVE_DELAY = 300


@dataclass(frozen=True)
class CalibrationStatistics:
    """Summary of valid allocation coefficients."""

    average: float
    minimum: float
    maximum: float
    standard_deviation: float
    coefficient_of_variation: float
    sample_count: int
    stable: bool


def calculate_statistics(coefficients: list[float]) -> CalibrationStatistics | None:
    """Calculate calibration statistics and stability."""
    if not coefficients:
        return None

    average = fmean(coefficients)
    minimum = min(coefficients)
    maximum = max(coefficients)
    standard_deviation = stdev(coefficients) if len(coefficients) > 1 else 0.0
    coefficient_of_variation = (
        standard_deviation / average if average > 0 else math.inf
    )
    relative_range = (maximum - minimum) / average if average > 0 else math.inf
    stable = (
        len(coefficients) >= PV_ALLOCATION_MIN_SAMPLES
        and coefficient_of_variation
        <= PV_ALLOCATION_MAX_COEFFICIENT_OF_VARIATION
        and relative_range <= PV_ALLOCATION_MAX_RELATIVE_RANGE
    )
    return CalibrationStatistics(
        average=average,
        minimum=minimum,
        maximum=maximum,
        standard_deviation=standard_deviation,
        coefficient_of_variation=coefficient_of_variation,
        sample_count=len(coefficients),
        stable=stable,
    )


class ApartmentPVAllocation:
    """Persist calibration and build a monotonic apartment PV estimate."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        flat_id: int,
    ) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.pv_allocation_flat_{flat_id}",
        )
        self._legacy_store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.pv_allocation_{entry_id}",
        )
        self._state: dict[str, Any] = self._empty_state()

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {
            "coefficient": None,
            "calibration_date": None,
            "sample_count": 0,
            "minimum": None,
            "maximum": None,
            "standard_deviation": None,
            "coefficient_of_variation": None,
            "calibration_stable": False,
            "stable": False,
            "unstable_logged": False,
            "zero_grid_skipped": [],
            "history": {},
            "estimated_total": 0.0,
            "estimated_today": 0.0,
            "estimate_date": None,
            "last_jom_register": None,
            "last_jom_daily": None,
            "active_coefficient": None,
            "cumulative_counters": {},
        }

    async def async_load(self) -> None:
        """Load persisted calibration and counter state."""
        stored = await self._store.async_load()
        if not isinstance(stored, dict):
            stored = await self._legacy_store.async_load()
            if isinstance(stored, dict):
                await self._store.async_save(stored)
                _LOGGER.info(
                    "Migrated SmartEV apartment PV allocation state to "
                    "stable apartment storage"
                )
        if not isinstance(stored, dict):
            return
        self._state.update(stored)
        if not isinstance(self._state.get("history"), dict):
            self._state["history"] = {}
        coefficient = self._finite_number(self._state.get("coefficient"))
        if coefficient is not None and coefficient >= 0:
            # A stored coefficient is the last accepted stable calibration.
            # Older state may contain stable=False from a later candidate
            # window; that must not disable the accepted coefficient.
            self._state["stable"] = True
        counters = self._state.setdefault("cumulative_counters", {})
        if not isinstance(counters, dict):
            counters = {}
            self._state["cumulative_counters"] = counters
        if "pv" not in counters:
            estimated_total = (
                self._finite_number(self._state.get("estimated_total")) or 0.0
            )
            estimated_today = (
                self._finite_number(self._state.get("estimated_today")) or 0.0
            )
            counters["pv"] = {
                "anchor": max(0.0, estimated_total - estimated_today),
                "total": estimated_total,
                "today": estimated_today,
                "date": self._state.get("estimate_date"),
                "last_source": self._finite_number(
                    self._state.get("last_jom_daily")
                ),
                "active_multiplier": self._finite_number(
                    self._state.get("active_coefficient")
                ),
                "last_rollover": None,
            }

    async def async_save(self) -> None:
        """Immediately persist state during config-entry unload."""
        await self._store.async_save(self._state)

    def update(
        self,
        now: datetime,
        jom_data: dict[str, Any] | None,
        apartment_daily_pv: dict[str, float] | None,
        apartment_daily_grid: dict[str, float] | None,
    ) -> dict[str, Any]:
        """Update calibration and estimates from one coordinator refresh."""
        today = now.date().isoformat()
        if jom_data is None:
            return self._result(today)

        register = jom_data.get("register")
        daily_jom = jom_data.get("daily")
        if (
            isinstance(register, bool)
            or not isinstance(register, (int, float))
            or not math.isfinite(register)
            or not isinstance(daily_jom, dict)
        ):
            return self._result(today)

        if apartment_daily_pv is not None and apartment_daily_grid is not None:
            self._calibrate(
                now,
                daily_jom,
                apartment_daily_pv,
                apartment_daily_grid,
            )

        coefficient = self._finite_number(self._state.get("coefficient"))
        if coefficient is None:
            self._state["last_jom_register"] = register
            self._state["last_jom_daily"] = self._finite_number(
                daily_jom.get(today)
            )
            self._schedule_save()
            return self._result(today)

        self._update_estimate(now, today, register, daily_jom, coefficient)
        self._schedule_save()
        return self._result(today)

    def _calibrate(
        self,
        now: datetime,
        daily_jom: dict[str, Any],
        apartment_daily_pv: dict[str, float],
        apartment_daily_grid: dict[str, float],
    ) -> None:
        """Join completed days and update coefficient statistics."""
        today = now.date().isoformat()
        history = self._state["history"]
        zero_grid_skipped = set(self._state.get("zero_grid_skipped") or [])
        history_changed = False
        for production_date, apartment_pv in apartment_daily_pv.items():
            if production_date >= today:
                continue
            jom_pv = self._finite_number(daily_jom.get(production_date))
            apartment_value = self._finite_number(apartment_pv)
            grid_import = self._finite_number(
                apartment_daily_grid.get(production_date)
            )
            if (
                jom_pv is None
                or jom_pv < PV_ALLOCATION_MIN_JOM_PRODUCTION
                or apartment_value is None
                or apartment_value < 0
                or apartment_value > jom_pv
                or grid_import is None
                or grid_import < 0
            ):
                continue
            if grid_import < PV_ALLOCATION_ZERO_GRID_IMPORT:
                zero_grid_skipped.add(production_date)
                if production_date in history:
                    history.pop(production_date)
                    history_changed = True
                continue

            zero_grid_skipped.discard(production_date)
            coefficient = apartment_value / jom_pv
            history_entry = {
                "coefficient": coefficient,
                "jom_pv": jom_pv,
                "apartment_pv": apartment_value,
            }
            if history.get(production_date) != history_entry:
                history[production_date] = history_entry
                history_changed = True

        self._state["zero_grid_skipped"] = sorted(zero_grid_skipped)[
            -PV_ALLOCATION_HISTORY_DAYS:
        ]

        # Older versions stored only the ratio, so their entries do not carry
        # the JOM production needed as a weight. Once weighted observations
        # are available, discard those legacy calibration samples while
        # preserving the active coefficient and cumulative energy counter.
        if any(isinstance(entry, dict) for entry in history.values()):
            for legacy_date in [
                production_date
                for production_date, entry in history.items()
                if not isinstance(entry, dict)
            ]:
                history.pop(legacy_date)
                history_changed = True

        for old_date in sorted(history)[:-PV_ALLOCATION_HISTORY_DAYS]:
            history.pop(old_date, None)
            history_changed = True

        current_dates = sorted(
            production_date for production_date in history if production_date < today
        )
        coefficients = [
            coefficient
            for production_date in current_dates
            if (
                coefficient := self._history_coefficient(history[production_date])
            )
            is not None
        ]
        stats = calculate_statistics(coefficients)
        if stats is None:
            return

        weighted_samples = [
            entry
            for production_date in current_dates
            if (entry := self._weighted_history_entry(history[production_date]))
            is not None
        ]
        total_jom_pv = sum(entry["jom_pv"] for entry in weighted_samples)
        if total_jom_pv <= 0:
            # Legacy stored entries contain only daily coefficients. Retain the
            # previous active coefficient until at least one report day has
            # been observed with its production weight.
            return
        weighted_coefficient = (
            sum(entry["apartment_pv"] for entry in weighted_samples)
            / total_jom_pv
        )

        previous = self._finite_number(self._state.get("coefficient"))
        self._state.update(
            {
                "sample_count": stats.sample_count,
                "minimum": stats.minimum,
                "maximum": stats.maximum,
                "standard_deviation": stats.standard_deviation,
                "coefficient_of_variation": stats.coefficient_of_variation,
                "calibration_stable": stats.stable,
            }
        )
        if not stats.stable:
            if (
                stats.sample_count >= PV_ALLOCATION_MIN_SAMPLES
                and not self._state.get("unstable_logged")
            ):
                _LOGGER.warning(
                    "Apartment PV allocation coefficients are not stable "
                    "(samples=%s, min=%.6f, max=%.6f, standard_deviation=%.6f); "
                    "the last accepted coefficient remains active",
                    stats.sample_count,
                    stats.minimum,
                    stats.maximum,
                    stats.standard_deviation,
                )
                self._state["unstable_logged"] = True
            return

        self._state["unstable_logged"] = False
        if previous is not None and previous > 0:
            relative_change = abs(weighted_coefficient - previous) / previous
            if relative_change > PV_ALLOCATION_SIGNIFICANT_CHANGE:
                _LOGGER.warning(
                    "Apartment PV allocation coefficient changed significantly "
                    "from %.6f to %.6f; the new value applies only to future "
                    "production",
                    previous,
                    weighted_coefficient,
                )

        self._state["coefficient"] = weighted_coefficient
        self._state["stable"] = True
        if history_changed or self._state.get("calibration_date") is None:
            self._state["calibration_date"] = now.isoformat()

    def _update_estimate(
        self,
        now: datetime,
        today: str,
        register: float,
        daily_jom: dict[str, Any],
        coefficient: float,
    ) -> None:
        """Accumulate only new JOM production using the active coefficient."""
        last_register = self._finite_number(self._state.get("last_jom_register"))
        current_daily = self._finite_number(daily_jom.get(today))
        counters = self._state.setdefault("cumulative_counters", {})
        counter_state = counters.setdefault(
            "pv", DailyCumulativeEnergyCounter.empty_state()
        )
        counter = DailyCumulativeEnergyCounter(counter_state)
        counter.update(now, current_daily, daily_jom, coefficient)
        self._state["estimate_date"] = counter_state["date"]
        self._state["estimated_today"] = counter_state["today"]
        self._state["estimated_total"] = counter_state["total"]

        if last_register is not None and register < last_register:
            _LOGGER.warning(
                "JOM PV cumulative register decreased from %.6f to %.6f; "
                "starting a new counter segment",
                last_register,
                register,
            )

        # Changing this value after accounting for the current register makes
        # recalibration affect future production only.
        self._state["active_coefficient"] = coefficient
        self._state["last_jom_register"] = register
        self._state["last_jom_daily"] = current_daily

    def update_grid(
        self,
        now: datetime,
        consumption_total: Any,
        pv_allocation_total: Any,
    ) -> dict[str, Any]:
        """Update cumulative grid import from consumption minus PV allocation."""
        counters = self._state.setdefault("cumulative_counters", {})
        counter_state = counters.get("grid")
        legacy_total = None
        if (
            not isinstance(counter_state, dict)
            or counter_state.get("mode") != "difference"
        ):
            if isinstance(counter_state, dict):
                legacy_total = self._finite_number(counter_state.get("total"))
            counter_state = DifferenceCumulativeEnergyCounter.empty_state()
            counters["grid"] = counter_state
        counter = DifferenceCumulativeEnergyCounter(counter_state)
        total = counter.update(
            consumption_total,
            pv_allocation_total,
            initial_total=legacy_total,
            now=now,
        )
        self._schedule_save()
        consumption = self._finite_number(consumption_total)
        allocation = self._finite_number(pv_allocation_total)
        return {
            "available": consumption is not None and allocation is not None,
            "total": total,
            **counter.attributes,
        }

    def _result(self, today: str) -> dict[str, Any]:
        """Return accepted cached values even if the latest input is missing."""
        coefficient = self._finite_number(self._state.get("coefficient"))
        estimated_today = self._finite_number(self._state.get("estimated_today"))
        estimated_total = self._finite_number(self._state.get("estimated_total"))
        total_available = coefficient is not None and estimated_total is not None
        today_available = (
            total_available
            and estimated_today is not None
            and self._state.get("estimate_date") == today
        )
        return {
            "available": total_available,
            "today_available": today_available,
            "estimated_today": estimated_today,
            "estimated_total": estimated_total,
            "allocation_coefficient": coefficient,
            "sample_days": self._state.get("sample_count", 0),
            "used_calibration_samples": self._state.get("sample_count", 0),
            "skipped_zero_grid_samples": len(
                self._state.get("zero_grid_skipped") or []
            ),
            "last_calibration": self._state.get("calibration_date"),
            "calibration_stable": self._state.get("calibration_stable"),
            "minimum_coefficient": self._state.get("minimum"),
            "maximum_coefficient": self._state.get("maximum"),
            "standard_deviation": self._state.get("standard_deviation"),
            "coefficient_of_variation": self._state.get(
                "coefficient_of_variation"
            ),
        }

    def _schedule_save(self) -> None:
        self._store.async_delay_save(lambda: self._state, _SAVE_DELAY)

    @staticmethod
    def _finite_number(value: Any) -> float | None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            return None
        return float(value)

    @classmethod
    def _history_coefficient(cls, entry: Any) -> float | None:
        """Return a daily coefficient from current or legacy storage."""
        if isinstance(entry, dict):
            return cls._finite_number(entry.get("coefficient"))
        return cls._finite_number(entry)

    @classmethod
    def _weighted_history_entry(cls, entry: Any) -> dict[str, float] | None:
        """Return the production values required for weighted calibration."""
        if not isinstance(entry, dict):
            return None
        coefficient = cls._finite_number(entry.get("coefficient"))
        jom_pv = cls._finite_number(entry.get("jom_pv"))
        apartment_pv = cls._finite_number(entry.get("apartment_pv"))
        if (
            coefficient is None
            or jom_pv is None
            or jom_pv <= 0
            or apartment_pv is None
            or apartment_pv < 0
        ):
            return None
        return {
            "coefficient": coefficient,
            "jom_pv": jom_pv,
            "apartment_pv": apartment_pv,
        }
