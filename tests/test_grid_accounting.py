"""Tests for authoritative apartment grid accounting."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import types
import unittest


def _load_accounting_class():
    """Load the module without importing Home Assistant integration setup."""
    source = Path(__file__).parents[1] / "custom_components" / "smartev"
    package_name = "_smartev_accounting_tests"
    package = types.ModuleType(package_name)
    package.__path__ = [str(source)]
    sys.modules[package_name] = package
    for module_name in ("const", "grid_accounting"):
        qualified_name = f"{package_name}.{module_name}"
        spec = importlib.util.spec_from_file_location(
            qualified_name, source / f"{module_name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[qualified_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return sys.modules[f"{package_name}.grid_accounting"].ApartmentGridAccounting


ApartmentGridAccounting = _load_accounting_class()


PRAGUE = timezone(timedelta(hours=2))


class FakeStore:
    """Minimal Home Assistant Store substitute."""

    def __init__(self, stored=None) -> None:
        self.stored = deepcopy(stored)
        self.pending = None

    async def async_load(self):
        return deepcopy(self.stored)

    async def async_save(self, value) -> None:
        self.stored = deepcopy(value)

    def async_delay_save(self, factory, _delay) -> None:
        self.pending = deepcopy(factory())

    def flush(self) -> None:
        self.stored = deepcopy(self.pending)


def at(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=PRAGUE)


class ApartmentGridAccountingTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.store = FakeStore()
        self.accounting = ApartmentGridAccounting(
            None, 200, store=self.store
        )
        await self.accounting.async_load()

    def update(self, when, official, estimate, legacy=None):
        return self.accounting.update(
            at(when), official, estimate, legacy_total=legacy
        )

    async def restart(self) -> None:
        self.store.flush()
        self.accounting = ApartmentGridAccounting(
            None, 200, store=self.store
        )
        await self.accounting.async_load()

    async def test_migration_establishes_baseline_without_increment(self):
        result = self.update(
            "2026-07-29T12:00:00",
            {"2026-07-28": 4.0},
            2.0,
            legacy=100.0,
        )

        self.assertEqual(result["total"], 100.0)
        self.assertEqual(result["migration_baseline_offset"], 94.0)
        self.assertEqual(result["continuity_offset"], 0.0)

    async def test_restart_during_migration_repeats_same_baseline(self):
        first = self.update(
            "2026-07-29T12:00:00",
            {"2026-07-28": 4.0},
            2.0,
            legacy=100.0,
        )
        # Simulate a crash before the delayed save is committed.
        self.accounting = ApartmentGridAccounting(
            None, 200, store=FakeStore()
        )
        await self.accounting.async_load()
        second = self.accounting.update(
            at("2026-07-29T12:01:00"),
            {"2026-07-28": 4.0},
            2.0,
            legacy_total=100.0,
        )

        self.assertEqual(first["total"], second["total"])
        self.assertEqual(second["total"], 100.0)

    async def test_repeated_import_is_idempotent(self):
        first = self.update(
            "2026-07-29T12:00:00",
            {"2026-07-28": 4.0},
            2.0,
        )
        second = self.update(
            "2026-07-29T12:01:00",
            {"2026-07-28": 4.0},
            2.0,
        )

        self.assertEqual(first["official_completed_total"], 4.0)
        self.assertEqual(second["official_completed_total"], 4.0)
        self.assertEqual(first["total"], second["total"])

    async def test_placeholder_is_ignored_but_completed_zero_is_accepted(self):
        result = self.update(
            "2026-07-29T12:00:00",
            {"2026-07-28": 0.0, "2026-07-29": 0.0},
            1.5,
        )

        self.assertEqual(result["last_official_date"], "2026-07-28")
        self.assertEqual(result["official_completed_total"], 0.0)
        self.assertEqual(result["current_month"], 1.5)

    async def test_delayed_report_replaces_pending_estimate(self):
        day_one = self.update("2026-07-29T23:59:00", {}, 5.0)
        before_report = self.update("2026-07-30T00:10:00", {}, 0.2)
        after_report = self.update(
            "2026-07-30T08:00:00", {"2026-07-29": 6.0}, 1.0
        )

        self.assertEqual(day_one["total"], 5.0)
        self.assertEqual(before_report["total"], 5.2)
        self.assertEqual(after_report["official_completed_total"], 6.0)
        self.assertEqual(after_report["current_month"], 7.0)
        self.assertEqual(after_report["total"], 7.0)

    async def test_lower_official_value_replaces_estimate_without_offset(self):
        self.update("2026-07-29T23:59:00", {}, 5.0)
        before = self.update("2026-07-30T08:00:00", {}, 1.0)
        after = self.update(
            "2026-07-30T08:01:00", {"2026-07-29": 3.0}, 1.0
        )

        self.assertEqual(before["total"], 6.0)
        self.assertEqual(after["total"], 6.0)
        self.assertEqual(after["official_completed_total"], 3.0)
        self.assertEqual(after["continuity_offset"], 0.0)
        self.assertEqual(after["current_month"], 4.0)

        caught_up = self.update(
            "2026-07-30T12:00:00", {"2026-07-29": 3.0}, 3.0
        )
        advanced = self.update(
            "2026-07-30T13:00:00", {"2026-07-29": 3.0}, 4.0
        )
        self.assertEqual(caught_up["total"], 6.0)
        self.assertEqual(caught_up["continuity_offset"], 0.0)
        self.assertEqual(advanced["total"], 7.0)

    async def test_downward_official_correction_uses_continuity_if_needed(self):
        before = self.update(
            "2026-07-29T12:00:00", {"2026-07-28": 5.0}, 1.0
        )
        corrected = self.update(
            "2026-07-29T12:01:00", {"2026-07-28": 3.0}, 1.0
        )

        self.assertEqual(before["total"], 6.0)
        self.assertEqual(corrected["official_completed_total"], 3.0)
        self.assertEqual(corrected["total"], 6.0)
        self.assertEqual(corrected["continuity_offset"], 2.0)

    async def test_official_correction_is_reconciled_once(self):
        self.update(
            "2026-07-29T12:00:00", {"2026-07-28": 4.0}, 1.0
        )
        corrected = self.update(
            "2026-07-29T12:01:00", {"2026-07-28": 4.5}, 1.0
        )
        repeated = self.update(
            "2026-07-29T12:02:00", {"2026-07-28": 4.5}, 1.0
        )

        self.assertEqual(corrected["official_completed_total"], 4.5)
        self.assertEqual(repeated["official_completed_total"], 4.5)

    async def test_temporary_csv_failure_keeps_official_days(self):
        first = self.update(
            "2026-07-29T12:00:00", {"2026-07-28": 4.0}, 1.0
        )
        failed = self.update("2026-07-29T12:01:00", None, 1.5)

        self.assertEqual(failed["official_completed_total"], 4.0)
        self.assertEqual(failed["current_month"], 5.5)
        self.assertGreaterEqual(failed["total"], first["total"])

    async def test_csv_failure_defers_migration_without_historical_jump(self):
        waiting = self.update(
            "2026-07-29T12:00:00", None, 2.0, legacy=100.0
        )
        migrated = self.update(
            "2026-07-29T12:01:00",
            {"2026-07-01": 20.0, "2026-07-28": 4.0},
            2.0,
            legacy=100.0,
        )

        self.assertEqual(waiting["total"], 100.0)
        self.assertEqual(migrated["total"], 100.0)
        self.assertEqual(migrated["migration_baseline_offset"], 74.0)

    async def test_month_and_year_rollover_keep_pending_estimate(self):
        self.update("2026-12-31T23:59:00", {}, 5.0)
        january = self.update("2027-01-01T00:10:00", {}, 0.2)
        reconciled = self.update(
            "2027-01-01T08:00:00", {"2026-12-31": 4.0}, 1.0
        )

        self.assertEqual(january["current_month"], 0.2)
        self.assertEqual(january["total"], 5.2)
        self.assertEqual(reconciled["current_month"], 1.0)
        self.assertGreaterEqual(reconciled["total"], january["total"])

    async def test_restart_before_publication_preserves_pending_estimate(self):
        self.update("2026-07-29T23:59:00", {}, 5.0)
        self.store.flush()
        await self.restart()
        before_report = self.update("2026-07-30T00:10:00", None, 0.2)
        self.store.flush()
        await self.restart()
        after_report = self.update(
            "2026-07-30T08:00:00", {"2026-07-29": 5.0}, 1.0
        )

        self.assertEqual(before_report["total"], 5.2)
        self.assertEqual(after_report["total"], 6.0)
        self.assertEqual(after_report["continuity_offset"], 0.0)

    async def test_migration_baseline_is_immutable_after_restart(self):
        migrated = self.update(
            "2026-07-29T12:00:00",
            {"2026-07-28": 4.0},
            2.0,
            legacy=100.0,
        )
        self.store.flush()
        await self.restart()
        updated = self.update(
            "2026-07-29T13:00:00",
            {"2026-07-28": 4.0},
            3.0,
            legacy=500.0,
        )

        self.assertEqual(
            updated["migration_baseline_offset"],
            migrated["migration_baseline_offset"],
        )
        self.assertEqual(updated["total"], 101.0)

    async def test_stale_continuity_migration_preserves_published_floor_once(self):
        legacy_state = {
            "mode": "authoritative_daily_grid",
            "official_total": 90.0,
            "recent_official": {"2026-07-28": 90.0},
            "pending_estimates": {},
            "estimate_date": "2026-07-28",
            "today_estimate": None,
            "migration_complete": True,
            "migration_baseline_offset": 0.0,
            "migration_reference_total": 90.0,
            "continuity_offset": 8.938,
            "published_total": 98.938,
            "last_official_date": "2026-07-28",
            "last_reconciliation": "2026-07-28T23:59:00+02:00",
        }
        self.store = FakeStore(legacy_state)
        self.accounting = ApartmentGridAccounting(
            None, 200, store=self.store
        )
        await self.accounting.async_load()

        held = self.update(
            "2026-07-29T08:00:00", {"2026-07-28": 90.0}, 1.0
        )
        caught_up = self.update(
            "2026-07-29T16:00:00", {"2026-07-28": 90.0}, 8.938
        )
        advanced = self.update(
            "2026-07-29T17:00:00", {"2026-07-28": 90.0}, 9.938
        )

        self.assertEqual(held["total"], 98.938)
        self.assertEqual(caught_up["total"], 98.938)
        self.assertEqual(advanced["total"], 99.938)
        self.assertEqual(held["continuity_offset"], 0.0)
        self.assertEqual(caught_up["continuity_offset"], 0.0)
        self.assertEqual(advanced["continuity_offset"], 0.0)
        self.assertEqual(self.store.stored["accounting_state_version"], 2)
        self.assertEqual(self.store.stored["published_total"], 98.938)

        # A legitimate post-migration official correction may establish new
        # continuity. Reloading the versioned state must not clear it again.
        corrected = self.update(
            "2026-07-29T17:01:00", {"2026-07-28": 89.0}, 9.938
        )
        self.assertEqual(corrected["total"], 99.938)
        self.assertEqual(corrected["continuity_offset"], 1.0)
        self.store.flush()
        await self.restart()
        after_restart = self.update(
            "2026-07-29T17:02:00", {"2026-07-28": 89.0}, 9.938
        )
        self.assertEqual(after_restart["total"], 99.938)
        self.assertEqual(after_restart["continuity_offset"], 1.0)


if __name__ == "__main__":
    unittest.main()
