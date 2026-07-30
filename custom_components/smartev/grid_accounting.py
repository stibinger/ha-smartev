# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

"""Persistent authoritative apartment grid-energy accounting."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1
_ACCOUNTING_STATE_VERSION = 2
_SAVE_DELAY = 300
_RECENT_DAYS = 70
_SIGNIFICANT_CORRECTION_KWH = 0.1


class ApartmentGridAccounting:
    """Combine authoritative completed days with a live current-day estimate."""

    def __init__(
        self,
        hass: HomeAssistant | None,
        flat_id: int,
        *,
        store: Any = None,
    ) -> None:
        if store is None:
            from homeassistant.helpers.storage import Store

            store = Store(
                hass,
                _STORAGE_VERSION,
                f"{DOMAIN}.grid_accounting_flat_{flat_id}",
            )
        self._store = store
        self._state: dict[str, Any] = self._empty_state()

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {
            "accounting_state_version": _ACCOUNTING_STATE_VERSION,
            "mode": "authoritative_daily_grid",
            "official_total": 0.0,
            "recent_official": {},
            "pending_estimates": {},
            "estimate_date": None,
            "today_estimate": None,
            "migration_complete": False,
            "migration_baseline_offset": None,
            "migration_reference_total": None,
            "continuity_offset": 0.0,
            "published_total": None,
            "last_official_date": None,
            "last_reconciliation": None,
        }

    async def async_load(self) -> None:
        """Load and normalize persisted accounting state."""
        stored = await self._store.async_load()
        if not isinstance(stored, dict):
            return
        self._state.update(stored)
        for key in ("recent_official", "pending_estimates"):
            if not isinstance(self._state.get(key), dict):
                self._state[key] = {}
        state_version = stored.get("accounting_state_version")
        if (
            not isinstance(state_version, int)
            or isinstance(state_version, bool)
            or state_version < _ACCOUNTING_STATE_VERSION
        ):
            stale_continuity = (
                self._valid_energy(self._state.get("continuity_offset")) or 0.0
            )
            self._state["continuity_offset"] = 0.0
            self._state["accounting_state_version"] = _ACCOUNTING_STATE_VERSION
            await self._store.async_save(self._state)
            _LOGGER.info(
                "Migrated SmartEV grid accounting state to version %d: "
                "removed stale continuity offset %.3f kWh while preserving "
                "published total %s",
                _ACCOUNTING_STATE_VERSION,
                stale_continuity,
                self._finite_number(self._state.get("published_total")),
            )

    async def async_save(self) -> None:
        """Immediately persist state during config-entry unload."""
        await self._store.async_save(self._state)

    def update(
        self,
        now: datetime,
        official_daily: dict[str, Any] | None,
        today_estimate: Any,
        *,
        legacy_total: Any = None,
    ) -> dict[str, Any]:
        """Reconcile official days and return period and cumulative totals."""
        today = now.date()
        today_iso = today.isoformat()
        estimate = self._valid_energy(today_estimate)
        report_available = official_daily is not None

        self._rollover_estimate(today_iso)
        official_correction_delta, reconciliation_date = self._reconcile_official(
            now, today, official_daily or {}
        )

        self._state["estimate_date"] = today_iso
        if estimate is not None:
            self._state["today_estimate"] = estimate

        raw_total = self._raw_total(today_iso)
        waiting_for_migration = False
        if not self._state.get("migration_complete"):
            if report_available:
                self._migrate(raw_total, legacy_total, now)
            else:
                waiting_for_migration = True
                legacy = self._valid_energy(legacy_total)
                if (
                    self._finite_number(self._state.get("published_total")) is None
                    and legacy is not None
                ):
                    self._state["published_total"] = legacy

        baseline = self._finite_number(
            self._state.get("migration_baseline_offset")
        ) or 0.0
        continuity = self._finite_number(
            self._state.get("continuity_offset")
        ) or 0.0
        previous = self._finite_number(self._state.get("published_total"))
        candidate = (
            previous
            if waiting_for_migration
            else raw_total + baseline + continuity
        )

        if (
            official_correction_delta < 0
            and previous is not None
            and candidate is not None
            and candidate < previous
        ):
            # Replacing a live estimate with an official completed-day value
            # must not permanently enter the difference into continuity.
            # Only the part of a decrease caused by correcting an already
            # official ledger entry is eligible for compensation.
            increase = min(previous - candidate, -official_correction_delta)
            continuity += increase
            self._state["continuity_offset"] = continuity
            candidate += increase
            log = (
                _LOGGER.info
                if abs(official_correction_delta) >= _SIGNIFICANT_CORRECTION_KWH
                else _LOGGER.debug
            )
            log(
                "SmartEV official grid reconciliation reduced the accounting "
                "total by %.3f kWh through %s; increased continuity offset by "
                "%.3f kWh to preserve the total-increasing sensor",
                abs(official_correction_delta),
                reconciliation_date,
                increase,
            )

        # A transient decrease in today's estimate is held without permanently
        # changing either offset. It can catch up on a later refresh.
        published = (
            max(previous, candidate)
            if previous is not None and candidate is not None
            else previous if candidate is None else candidate
        )
        self._state["published_total"] = published
        self._prune(today)
        self._debug_dump_ledger(today_iso, baseline, continuity, published)
        self._schedule_save()

        month_prefix = today.strftime("%Y-%m-")
        completed_month = sum(
            value
            for production_date, raw_value in self._state["recent_official"].items()
            if production_date.startswith(month_prefix)
            and production_date < today_iso
            and (value := self._valid_energy(raw_value)) is not None
        )
        current_estimate = (
            estimate
            if estimate is not None
            else self._estimate_for_date(today_iso)
        )
        month_total = (
            completed_month + current_estimate
            if current_estimate is not None
            else None
        )

        result = {
            "available": published is not None,
            "today": current_estimate,
            "current_month": month_total,
            "total": published,
            "today_source": "estimate",
            "last_official_date": self._state.get("last_official_date"),
            "migration_baseline_offset": baseline,
            "migration_reference_total": self._finite_number(
                self._state.get("migration_reference_total")
            ),
            "continuity_offset": continuity,
            "last_reconciliation": self._state.get("last_reconciliation"),
            "official_completed_total": self._finite_number(
                self._state.get("official_total")
            ),
            "today_estimate": current_estimate,
        }
        _LOGGER.debug(
            "SmartEV grid publication pipeline: stage=accounting_update "
            "published_total=%s result_total=%s",
            published,
            result["total"],
        )
        return result

    def _rollover_estimate(self, today: str) -> None:
        previous_date = self._state.get("estimate_date")
        previous_estimate = self._valid_energy(self._state.get("today_estimate"))
        if (
            isinstance(previous_date, str)
            and previous_date < today
            and previous_estimate is not None
            and previous_date not in self._state["recent_official"]
        ):
            self._state["pending_estimates"][previous_date] = previous_estimate
        if previous_date != today:
            self._state["today_estimate"] = None

    def _reconcile_official(
        self,
        now: datetime,
        today: date,
        official_daily: dict[str, Any],
    ) -> tuple[float, str | None]:
        recent = self._state["recent_official"]
        pending = self._state["pending_estimates"]
        official_total = (
            self._finite_number(self._state.get("official_total")) or 0.0
        )
        cutoff = (today - timedelta(days=_RECENT_DAYS)).isoformat()
        official_correction_total = 0.0
        changed = False
        last_changed_date = None

        for production_date, raw_value in sorted(official_daily.items()):
            value = self._valid_energy(raw_value)
            parsed_date = self._parse_date(production_date)
            if value is None or parsed_date is None or parsed_date >= today:
                continue
            if production_date < cutoff and production_date not in recent:
                _LOGGER.debug(
                    "Ignoring SmartEV grid day %s outside the reconciliation window",
                    production_date,
                )
                continue

            ledger_before = {
                "official_total": official_total,
                "recent_official": dict(recent),
                "pending_estimates": dict(pending),
            }
            had_official = production_date in recent
            previous_official = self._valid_energy(recent.get(production_date))
            previous_estimate = self._valid_energy(pending.pop(production_date, None))
            if previous_official is None:
                official_delta = value
            else:
                official_delta = value - previous_official
                official_correction_total += official_delta

            if had_official and official_delta == 0 and previous_estimate is None:
                continue
            official_total += official_delta
            recent[production_date] = value
            changed = True
            last_changed_date = production_date
            _LOGGER.debug(
                "Reconciled SmartEV apartment grid day: processed_date=%s, "
                "official_grid_csv=%.3f kWh, previous_official=%s, "
                "previous_estimate=%s, ledger_before=%s, ledger_after=%s",
                production_date,
                value,
                previous_official,
                previous_estimate,
                ledger_before,
                {
                    "official_total": official_total,
                    "recent_official": dict(recent),
                    "pending_estimates": dict(pending),
                },
            )

        if changed:
            self._state["official_total"] = official_total
            self._state["last_official_date"] = max(recent)
            self._state["last_reconciliation"] = now.isoformat()
        return official_correction_total, last_changed_date

    def _migrate(self, raw_total: float, legacy_total: Any, now: datetime) -> None:
        legacy = self._valid_energy(legacy_total)
        baseline = legacy - raw_total if legacy is not None else 0.0
        reference = legacy if legacy is not None else raw_total
        self._state.update(
            {
                "migration_baseline_offset": baseline,
                "migration_reference_total": reference,
                "continuity_offset": 0.0,
                "published_total": reference,
                "migration_complete": True,
                "last_reconciliation": now.isoformat(),
            }
        )
        _LOGGER.debug(
            "Initialized SmartEV authoritative grid accounting at %.3f kWh "
            "with migration baseline offset %.3f kWh",
            reference,
            baseline,
        )

    def _raw_total(self, today: str) -> float:
        official = self._finite_number(self._state.get("official_total")) or 0.0
        pending = sum(
            value
            for raw_value in self._state["pending_estimates"].values()
            if (value := self._valid_energy(raw_value)) is not None
        )
        estimate = self._estimate_for_date(today) or 0.0
        return official + pending + estimate

    def _estimate_for_date(self, production_date: str) -> float | None:
        if self._state.get("estimate_date") != production_date:
            return None
        return self._valid_energy(self._state.get("today_estimate"))

    def _debug_dump_ledger(
        self,
        today: str,
        migration_baseline_offset: float,
        continuity_offset: float,
        published_total: float | None,
    ) -> None:
        """Log the complete retained daily ledger after reconciliation."""
        if not _LOGGER.isEnabledFor(logging.DEBUG):
            return

        rows: list[tuple[str, str, float]] = []
        for production_date, raw_value in self._state["recent_official"].items():
            if (value := self._valid_energy(raw_value)) is not None:
                rows.append((production_date, "official", value))
        for production_date, raw_value in self._state["pending_estimates"].items():
            if (value := self._valid_energy(raw_value)) is not None:
                rows.append((production_date, "estimate", value))
        if (value := self._estimate_for_date(today)) is not None:
            rows.append((today, "estimate", value))

        pending_total = sum(
            value
            for raw_value in self._state["pending_estimates"].values()
            if (value := self._valid_energy(raw_value)) is not None
        )
        daily_lines = (
            "\n".join(
                f"  date={production_date} source={source} grid={value:.3f} kWh"
                for production_date, source, value in sorted(rows)
            )
            or "  <no stored days>"
        )
        _LOGGER.debug(
            "SmartEV ApartmentGridAccounting ledger after reconciliation "
            "(processed_date=%s):\n%s\n"
            "  official_completed_total=%.3f kWh\n"
            "  pending_total=%.3f kWh\n"
            "  today_estimate=%s\n"
            "  migration_baseline_offset=%.3f kWh\n"
            "  continuity_offset=%.3f kWh\n"
            "  published_total=%s",
            today,
            daily_lines,
            self._finite_number(self._state.get("official_total")) or 0.0,
            pending_total,
            self._estimate_for_date(today),
            migration_baseline_offset,
            continuity_offset,
            published_total,
        )

    def _prune(self, today: date) -> None:
        cutoff = (today - timedelta(days=_RECENT_DAYS)).isoformat()
        for key in ("recent_official", "pending_estimates"):
            values = self._state[key]
            for production_date in list(values):
                if production_date < cutoff:
                    values.pop(production_date, None)

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
        return number if number is not None and number >= 0 else None
