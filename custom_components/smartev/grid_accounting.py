# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

"""Persistent accounting for completed SmartEV daily energy values."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 3
_SAVE_DELAY = 300


class ApartmentGridAccounting:
    """Publish only completed SmartEV days as cumulative accounting energy.

    The current-day estimate is deliberately kept outside ``total`` and
    ``current_month``. SmartEV can revise the current-day apartment allocation
    while the day is still open, so including it in a Home Assistant TOTAL
    sensor would allow the cumulative value to decrease.
    """

    def __init__(
        self,
        hass: HomeAssistant | None,
        flat_id: int,
        *,
        store: Any = None,
        storage_name: str = "grid_accounting",
    ) -> None:
        if store is None:
            from homeassistant.helpers.storage import Store

            store = Store(
                hass,
                _STORAGE_VERSION,
                f"{DOMAIN}.{storage_name}_flat_{flat_id}",
            )
        self._store = store
        self._state: dict[str, Any] = self._empty_state()

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {
            "official_total": 0.0,
            "recent_official": {},
            "last_official_date": None,
            "last_reconciliation": None,
        }

    async def async_load(self) -> None:
        """Load persisted completed-day accounting state."""
        stored = await self._store.async_load()
        if not isinstance(stored, dict):
            return

        allowed = self._empty_state()
        for key in allowed:
            if key in stored:
                allowed[key] = stored[key]
        self._state = allowed
        if not isinstance(self._state.get("recent_official"), dict):
            self._state["recent_official"] = {}

    async def async_save(self) -> None:
        """Immediately persist state during config-entry unload."""
        await self._store.async_save(self._state)

    def update(
        self,
        now: datetime,
        official_daily: dict[str, Any] | None,
        today_estimate: Any,
    ) -> dict[str, Any]:
        """Return completed SmartEV accounting plus a separate live estimate."""
        today = now.date()
        today_iso = today.isoformat()
        estimate = self._valid_energy(today_estimate)

        self._reconcile_official(now, today, official_daily or {})
        self._schedule_save()

        completed = {
            production_date: value
            for production_date, raw_value in self._state["recent_official"].items()
            if production_date < today_iso
            and (value := self._valid_energy(raw_value)) is not None
        }
        month_prefix = today.strftime("%Y-%m-")
        completed_month = sum(
            value
            for production_date, value in completed.items()
            if production_date.startswith(month_prefix)
        )
        # Recompute from authoritative rows on every update.  This makes SmartEV
        # corrections idempotent and eliminates continuity/pending offsets.
        official_total = sum(completed.values())
        self._state["official_total"] = official_total

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "SmartEV completed-day accounting: processed_date=%s "
                "official_total=%.3f kWh completed_month=%.3f kWh "
                "today_estimate=%s (excluded from cumulative totals)",
                today_iso,
                official_total,
                completed_month,
                estimate,
            )

        return {
            "available": True,
            "today": estimate,
            "current_month": completed_month,
            "total": official_total,
            "today_source": "estimate",
            "cumulative_source": "official_completed_days",
            "last_official_date": self._state.get("last_official_date"),
            "last_reconciliation": self._state.get("last_reconciliation"),
            "official_completed_total": official_total,
            "today_estimate": estimate,
        }

    def _reconcile_official(
        self,
        now: datetime,
        today: date,
        official_daily: dict[str, Any],
    ) -> None:
        recent = self._state["recent_official"]
        changed = False

        for production_date, raw_value in sorted(official_daily.items()):
            value = self._valid_energy(raw_value)
            parsed_date = self._parse_date(production_date)
            if value is None or parsed_date is None or parsed_date >= today:
                continue

            previous_official = self._valid_energy(recent.get(production_date))
            if previous_official == value:
                continue

            recent[production_date] = value
            changed = True

        if changed:
            self._state["last_official_date"] = max(recent) if recent else None
            self._state["last_reconciliation"] = now.isoformat()

    def _schedule_save(self) -> None:
        delay_save = getattr(self._store, "async_delay_save", None)
        if delay_save is not None:
            delay_save(lambda: self._state, _SAVE_DELAY)

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not isinstance(value, str):
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

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
    def _valid_energy(cls, value: Any) -> float | None:
        number = cls._finite_number(value)
        if number is None or number < 0:
            return None
        return number
