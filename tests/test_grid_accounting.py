"""Tests for completed-day SmartEV accounting."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _load_accounting_class():
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
        self.accounting = ApartmentGridAccounting(None, 200, store=self.store)
        await self.accounting.async_load()

    def update(self, when, official, estimate):
        return self.accounting.update(at(when), official, estimate)

    async def restart(self) -> None:
        self.store.flush()
        self.accounting = ApartmentGridAccounting(None, 200, store=self.store)
        await self.accounting.async_load()

    async def test_today_estimate_is_not_in_cumulative_total(self):
        result = self.update("2026-07-29T12:00:00", {"2026-07-28": 4.0}, 2.0)
        self.assertEqual(result["today"], 2.0)
        self.assertEqual(result["current_month"], 4.0)
        self.assertEqual(result["total"], 4.0)
        self.assertEqual(result["cumulative_source"], "official_completed_days")

    async def test_falling_today_estimate_cannot_reduce_total(self):
        first = self.update("2026-07-29T12:00:00", {"2026-07-28": 4.0}, 1.25)
        second = self.update("2026-07-29T13:00:00", {"2026-07-28": 4.0}, 0.40)
        third = self.update("2026-07-29T14:00:00", {"2026-07-28": 4.0}, 0.0)
        self.assertEqual(first["total"], 4.0)
        self.assertEqual(second["total"], 4.0)
        self.assertEqual(third["total"], 4.0)
        self.assertEqual(third["today"], 0.0)

    async def test_today_official_placeholder_is_ignored(self):
        result = self.update(
            "2026-07-29T12:00:00",
            {"2026-07-28": 3.0, "2026-07-29": 99.0},
            1.0,
        )
        self.assertEqual(result["official_completed_total"], 3.0)
        self.assertEqual(result["total"], 3.0)

    async def test_new_completed_day_is_added_once(self):
        before = self.update("2026-07-29T23:59:00", {"2026-07-28": 4.0}, 2.0)
        after = self.update(
            "2026-07-30T08:00:00",
            {"2026-07-28": 4.0, "2026-07-29": 2.069},
            0.5,
        )
        repeated = self.update(
            "2026-07-30T08:01:00",
            {"2026-07-28": 4.0, "2026-07-29": 2.069},
            0.6,
        )
        self.assertEqual(before["total"], 4.0)
        self.assertEqual(after["total"], 6.069)
        self.assertEqual(repeated["total"], 6.069)

    async def test_month_rollover_excludes_new_day_estimate(self):
        july = self.update("2026-07-31T23:59:00", {"2026-07-30": 5.0}, 2.23)
        august = self.update(
            "2026-08-01T08:00:00",
            {"2026-07-30": 5.0, "2026-07-31": 2.069},
            0.5,
        )
        self.assertEqual(july["total"], 5.0)
        self.assertEqual(august["total"], 7.069)
        self.assertEqual(august["current_month"], 0.0)
        self.assertEqual(august["today"], 0.5)

    async def test_restart_preserves_completed_total_only(self):
        self.update("2026-07-29T12:00:00", {"2026-07-28": 4.0}, 1.5)
        self.store.flush()
        await self.restart()
        result = self.update("2026-07-29T13:00:00", None, 0.2)
        self.assertEqual(result["total"], 4.0)
        self.assertEqual(result["today"], 0.2)

    async def test_completed_zero_is_authoritative(self):
        result = self.update("2026-07-29T12:00:00", {"2026-07-28": 0.0}, 1.5)
        self.assertEqual(result["last_official_date"], "2026-07-28")
        self.assertEqual(result["official_completed_total"], 0.0)
        self.assertEqual(result["current_month"], 0.0)

    async def test_31_july_reference_value_is_exact(self):
        result = self.update(
            "2026-08-01T08:00:00", {"2026-07-31": 2.069}, 0.5
        )
        self.assertEqual(result["official_completed_total"], 2.069)
        self.assertEqual(result["total"], 2.069)
        self.assertEqual(result["today"], 0.5)
        self.assertEqual(result["last_official_date"], "2026-07-31")

    async def test_full_year_history_is_rebuilt_from_authoritative_rows(self):
        result = self.update(
            "2026-08-02T12:00:00",
            {
                "2026-01-01": 1.25,
                "2026-07-31": 2.069,
                "2026-08-01": 5.548,
                "2026-08-02": 99.0,
            },
            0.3,
        )
        self.assertAlmostEqual(result["total"], 8.867)
        self.assertAlmostEqual(result["current_month"], 5.548)
        self.assertEqual(result["last_official_date"], "2026-08-01")

    async def test_historical_correction_recomputes_total_without_offset(self):
        first = self.update(
            "2026-08-02T12:00:00",
            {"2026-01-01": 2.0, "2026-08-01": 5.548},
            0.3,
        )
        corrected = self.update(
            "2026-08-02T12:01:00",
            {"2026-01-01": 1.5, "2026-08-01": 5.548},
            0.3,
        )
        self.assertAlmostEqual(first["total"], 7.548)
        self.assertAlmostEqual(corrected["total"], 7.048)


if __name__ == "__main__":
    unittest.main()
