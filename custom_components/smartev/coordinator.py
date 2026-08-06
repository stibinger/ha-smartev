# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

from datetime import date, datetime, timedelta
import logging

import requests
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .allocation import ApartmentPVAllocation
from .client import SmartEVAuthenticationError
from .grid_accounting import ApartmentGridAccounting
from .energy_statistics import async_publish_completed_day_statistics

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_UPDATE_INTERVAL = timedelta(hours=1)
_DAILY_REPORT_INTERVAL = timedelta(days=1)
_HISTORY_REFRESH_INTERVAL = timedelta(days=7)
_CACHE_VERSION = 1


class SmartEVCoordinator(DataUpdateCoordinator[dict]):
    """SmartEV data coordinator with rate-limited server access."""

    def __init__(self, hass: HomeAssistant, client, entry_id: str, flat_id: int) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=_UPDATE_INTERVAL,
        )
        self.client = client
        self.pv_allocation = ApartmentPVAllocation(hass, entry_id, flat_id)
        self.grid_accounting = ApartmentGridAccounting(hass, flat_id)
        self.pv_accounting = ApartmentGridAccounting(
            hass, flat_id, storage_name="pv_accounting"
        )
        self.flat_id = flat_id
        self._cache: Store[dict] = Store(
            hass, _CACHE_VERSION, f"{DOMAIN}.server_cache_flat_{flat_id}"
        )
        self._official_year_pv: dict[str, float] = {}
        self._official_year_grid: dict[str, float] = {}
        self._current_month_production: dict | None = None
        self._last_daily_report_refresh: datetime | None = None
        self._last_history_refresh: datetime | None = None
        self._published_statistics_signature: tuple | None = None

    async def async_load(self) -> None:
        """Load persistent estimator, accounting, and server-cache state."""
        await self.pv_allocation.async_load()
        await self.grid_accounting.async_load()
        await self.pv_accounting.async_load()

        # v0.7.2 already persisted authoritative rows in the accounting stores.
        # Reuse them so an upgrade/restart does not trigger a full historical
        # download merely to reconstruct data Home Assistant already has.
        self._official_year_grid = self.grid_accounting.official_daily()
        self._official_year_pv = self.pv_accounting.official_daily()

        cached = await self._cache.async_load()
        if not isinstance(cached, dict):
            return
        cached_pv = cached.get("official_year_pv")
        cached_grid = cached.get("official_year_grid")
        if isinstance(cached_pv, dict):
            self._official_year_pv.update(cached_pv)
        if isinstance(cached_grid, dict):
            self._official_year_grid.update(cached_grid)
        production = cached.get("current_month_production")
        if isinstance(production, dict):
            self._current_month_production = production
        self._last_daily_report_refresh = self._parse_datetime(
            cached.get("last_daily_report_refresh")
        )
        self._last_history_refresh = self._parse_datetime(
            cached.get("last_history_refresh")
        )

    async def async_shutdown(self) -> None:
        """Persist state before unloading."""
        await self.pv_allocation.async_save()
        await self.grid_accounting.async_save()
        await self.pv_accounting.async_save()
        await self._async_save_cache()

    async def _async_update_data(self):
        """Fetch hourly live data and rate-limited aggregate data from SmartEV."""
        try:
            now = dt_util.now()
            if (
                self._last_history_refresh is None
                and (self._official_year_pv or self._official_year_grid)
            ):
                # Seed the correction timer when upgrading from v0.7.2 without
                # forcing an immediate historical download.
                self._last_history_refresh = now
                await self._async_save_cache()
            refresh_daily = self._daily_report_due(now)
            refresh_history = self._history_refresh_due(now)
            (
                data,
                current_year_data,
                current_month_data,
                jom_pv_data,
                current_month_production,
                cache_changed,
            ) = await self.hass.async_add_executor_job(
                self._get_consumption_data,
                now.year,
                now.month,
                now.date(),
                refresh_daily,
                refresh_history,
            )

            if cache_changed:
                await self._async_save_cache()

            data["currentYearConsumption"] = self._period_value(data, now.year)
            data["currentMonthConsumption"] = self._period_value(
                current_year_data, now.month
            )
            data["todayConsumption"] = self._period_value(
                current_month_data, now.day
            )
            data["currentMonthProduction"] = None
            data["latestDailyProduction"] = None
            data["latestDailyProductionDate"] = None
            if current_month_production is not None:
                data["currentMonthProduction"] = current_month_production["pv"]["total"]
                latest = current_month_production["pv"].get("latest_daily")
                if latest is not None:
                    data["latestDailyProductionDate"], data["latestDailyProduction"] = latest

            data["dailyAggregation"] = current_month_data
            apartment_daily_pv = (
                current_month_production["pv"]["calibration_daily"]
                if current_month_production is not None
                else self._official_year_pv
            )
            apartment_daily_grid = (
                current_month_production["grid"]["calibration_daily"]
                if current_month_production is not None
                else self._official_year_grid
            )
            data["pvAllocation"] = self.pv_allocation.update(
                now, jom_pv_data, apartment_daily_pv, apartment_daily_grid
            )
            allocation = data["pvAllocation"]
            estimated_today = (
                allocation.get("estimated_today")
                if allocation.get("today_available")
                else None
            )
            today_grid_estimate = self._difference(
                data["todayConsumption"], estimated_today
            )
            data["pvAccounting"] = self.pv_accounting.update(
                now, self._official_year_pv, estimated_today
            )
            data["gridAccounting"] = self.grid_accounting.update(
                now, self._official_year_grid, today_grid_estimate
            )
            data["todayGridEnergy"] = data["gridAccounting"]["today"]
            data["currentMonthGridEnergy"] = data["gridAccounting"]["current_month"]
            data["gridCumulative"] = data["gridAccounting"]
            data["officialYearPV"] = dict(self._official_year_pv)
            data["officialYearGrid"] = dict(self._official_year_grid)

            statistics_signature = (
                now.date(),
                tuple(sorted(self._official_year_grid.items())),
                tuple(sorted(self._official_year_pv.items())),
            )
            if statistics_signature != self._published_statistics_signature:
                async_publish_completed_day_statistics(
                    self.hass,
                    self.flat_id,
                    now.date(),
                    self._official_year_grid,
                    self._official_year_pv,
                )
                self._published_statistics_signature = statistics_signature
            return data
        except SmartEVAuthenticationError as err:
            raise ConfigEntryAuthFailed("SmartEV authentication failed") from err
        except requests.HTTPError as err:
            status_code = err.response.status_code if err.response is not None else None
            if status_code in (401, 403):
                raise ConfigEntryAuthFailed("SmartEV authentication failed") from err
            raise UpdateFailed(f"Error communicating with SmartEV: {err}") from err
        except (requests.RequestException, ValueError) as err:
            raise UpdateFailed(f"Error communicating with SmartEV: {err}") from err

    def _get_consumption_data(
        self,
        year: int,
        month: int,
        today: date,
        refresh_daily: bool,
        refresh_history: bool,
    ) -> tuple[dict, dict, dict, dict | None, dict | None, bool]:
        """Fetch shared server data while keeping expensive reports rate-limited."""
        # These five calls provide the hourly entities.  No entity performs its
        # own polling, so all sensors share this single coordinator refresh.
        data = self.client.get_flat_info()
        live_flat = self.client.get_live_flat_info(data["buildingId"])
        live_meter = live_flat["meters"][0]
        data["meters"][0].update(
            {
                key: live_meter.get(key)
                for key in ("id", "dt", "type", "value1", "value2", "unit")
            }
        )
        current_year_data = self.client.get_flat_info(year=year)
        current_month_data = self.client.get_flat_info(year=year, month=month)
        try:
            jom_pv_data = self.client.get_jom_pv_data(year=year, month=month)
        except (requests.RequestException, ValueError) as err:
            _LOGGER.debug("Unable to update optional SmartEV JOM PV data: %s", err)
            jom_pv_data = None

        cache_changed = False
        now = dt_util.now()

        # A fresh installation needs authoritative history once.  Afterwards a
        # weekly refresh is enough to pick up rare SmartEV historical corrections.
        if refresh_history:
            year_pv: dict[str, float] = {}
            year_grid: dict[str, float] = {}
            latest_report: dict | None = None
            for history_month in range(1, month + 1):
                try:
                    report = self.client.get_production_report(year=year, month=history_month)
                except (requests.RequestException, ValueError) as err:
                    _LOGGER.warning(
                        "Unable to refresh SmartEV production history for %04d-%02d: %s",
                        year,
                        history_month,
                        err,
                    )
                    continue
                year_pv.update(report["pv"]["daily"])
                year_grid.update(report["grid"]["daily"])
                if history_month == month:
                    latest_report = report
            if year_pv or year_grid:
                self._official_year_pv.update(year_pv)
                self._official_year_grid.update(year_grid)
                self._last_history_refresh = now
                cache_changed = True
            if latest_report is not None:
                self._current_month_production = latest_report
                self._last_daily_report_refresh = now
                refresh_daily = False
                cache_changed = True

        # The current-month CSV contains completed apartment PV/grid values and
        # changes only on a daily boundary.  Fetch it at most once per day.
        if refresh_daily:
            try:
                report = self.client.get_production_report(year=year, month=month)
                self._current_month_production = report
                self._official_year_pv.update(report["pv"]["daily"])
                self._official_year_grid.update(report["grid"]["daily"])
                self._last_daily_report_refresh = now
                cache_changed = True
            except (requests.RequestException, ValueError) as err:
                _LOGGER.debug("Unable to update optional SmartEV production data: %s", err)

        current_month_production = self._prepare_production(today)
        return (
            data,
            current_year_data,
            current_month_data,
            jom_pv_data,
            current_month_production,
            cache_changed,
        )

    def _prepare_production(self, today: date) -> dict | None:
        """Build the production structure consumed by sensors and accounting."""
        source = self._current_month_production
        if not isinstance(source, dict):
            if not self._official_year_pv and not self._official_year_grid:
                return None
            source = {"pv": {"total": 0.0, "daily": {}}, "grid": {"total": 0.0, "daily": {}}}

        pv = source.get("pv") if isinstance(source.get("pv"), dict) else {}
        grid = source.get("grid") if isinstance(source.get("grid"), dict) else {}
        daily_pv = dict(pv.get("daily") or {})
        daily_grid = dict(grid.get("daily") or {})
        latest = self._latest_completed_daily_value(self._official_year_pv, today)
        month_prefix = today.strftime("%Y-%m-")
        completed_month_pv = sum(
            value
            for production_date, value in self._official_year_pv.items()
            if production_date.startswith(month_prefix) and production_date < today.isoformat()
        )
        completed_month_grid = sum(
            value
            for production_date, value in self._official_year_grid.items()
            if production_date.startswith(month_prefix) and production_date < today.isoformat()
        )
        return {
            "pv": {
                "total": completed_month_pv,
                "daily": daily_pv,
                "latest_daily": latest,
                "calibration_daily": dict(self._official_year_pv),
            },
            "grid": {
                "total": completed_month_grid,
                "daily": daily_grid,
                "calibration_daily": dict(self._official_year_grid),
                "accounting_daily": dict(self._official_year_grid),
            },
        }

    def _daily_report_due(self, now: datetime) -> bool:
        """Refresh the completed-day CSV once per local day after 09:00."""
        last = self._last_daily_report_refresh
        if last is not None and last.date() >= now.date():
            return False
        # SmartEV publishes completed apartment allocation with a delay.  Avoid
        # an unnecessary just-after-midnight request that is likely to return
        # the previous state; the hourly coordinator will pick it up after 09:00.
        return now.hour >= 9

    def _history_refresh_due(self, now: datetime) -> bool:
        # If no persisted authoritative rows exist, bootstrap immediately.
        if not self._official_year_pv and not self._official_year_grid:
            return True
        last = self._last_history_refresh
        if last is None:
            return False
        return now - last >= _HISTORY_REFRESH_INTERVAL

    async def _async_save_cache(self) -> None:
        await self._cache.async_save(
            {
                "official_year_pv": self._official_year_pv,
                "official_year_grid": self._official_year_grid,
                "current_month_production": self._current_month_production,
                "last_daily_report_refresh": self._format_datetime(self._last_daily_report_refresh),
                "last_history_refresh": self._format_datetime(self._last_history_refresh),
            }
        )

    @staticmethod
    def _format_datetime(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _parse_datetime(value) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _latest_completed_daily_value(
        daily_values: dict[str, float], today: date
    ) -> tuple[str, float] | None:
        today_iso = today.isoformat()
        return max(
            (
                (production_date, value)
                for production_date, value in daily_values.items()
                if production_date < today_iso
            ),
            default=None,
        )

    @staticmethod
    def _period_value(data: dict, index: int) -> int | float | None:
        meters = data.get("meters")
        if not meters:
            return None
        for item in meters[0].get("chartData") or []:
            if not isinstance(item, dict):
                continue
            if str(item.get("idx", "")).lstrip("0") == str(index):
                value = item.get("val1")
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    return value
                return None
        return None

    @staticmethod
    def _difference(
        consumption: int | float | None,
        pv_allocation: int | float | None,
    ) -> float | None:
        if (
            isinstance(consumption, bool)
            or not isinstance(consumption, (int, float))
            or isinstance(pv_allocation, bool)
            or not isinstance(pv_allocation, (int, float))
        ):
            return None
        return max(0.0, float(consumption) - float(pv_allocation))
