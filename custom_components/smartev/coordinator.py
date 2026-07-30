# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

from datetime import date, timedelta
import logging

import requests
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .allocation import ApartmentPVAllocation
from .client import SmartEVAuthenticationError
from .grid_accounting import ApartmentGridAccounting

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SmartEVCoordinator(DataUpdateCoordinator[dict]):
    """SmartEV data coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        client,
        entry_id: str,
        flat_id: int,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )

        self.client = client
        self.pv_allocation = ApartmentPVAllocation(
            hass,
            entry_id,
            flat_id,
        )
        self.grid_accounting = ApartmentGridAccounting(hass, flat_id)

    async def async_load(self) -> None:
        """Load persistent estimator state before the first refresh."""
        await self.pv_allocation.async_load()
        await self.grid_accounting.async_load()

    async def async_shutdown(self) -> None:
        """Persist estimator state before unloading."""
        await self.pv_allocation.async_save()
        await self.grid_accounting.async_save()

    async def _async_update_data(self):
        """Fetch data from SmartEV."""
        try:
            now = dt_util.now()
            (
                data,
                current_year_data,
                current_month_data,
                current_month_production,
                jom_pv_data,
            ) = (
                await self.hass.async_add_executor_job(
                    self._get_consumption_data, now.year, now.month, now.date()
                )
            )

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
                data["currentMonthProduction"] = current_month_production["pv"][
                    "total"
                ]
                latest_daily_production = current_month_production["pv"].get(
                    "latest_daily"
                )
                if latest_daily_production is not None:
                    (
                        data["latestDailyProductionDate"],
                        data["latestDailyProduction"],
                    ) = latest_daily_production
            data["dailyAggregation"] = current_month_data
            apartment_daily_pv = (
                current_month_production["pv"]["calibration_daily"]
                if current_month_production is not None
                else None
            )
            apartment_daily_grid = (
                current_month_production["grid"]["calibration_daily"]
                if current_month_production is not None
                else None
            )
            data["pvAllocation"] = self.pv_allocation.update(
                now,
                jom_pv_data,
                apartment_daily_pv,
                apartment_daily_grid,
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
            official_daily_grid = (
                current_month_production["grid"]["accounting_daily"]
                if current_month_production is not None
                else None
            )
            data["gridAccounting"] = self.grid_accounting.update(
                now,
                official_daily_grid,
                today_grid_estimate,
                legacy_total=self.pv_allocation.legacy_grid_total(),
            )
            _LOGGER.debug(
                "SmartEV grid publication pipeline: stage=coordinator_result "
                "accounting_published_total=%s",
                data["gridAccounting"].get("total"),
            )
            data["todayGridEnergy"] = data["gridAccounting"]["today"]
            data["currentMonthGridEnergy"] = data["gridAccounting"][
                "current_month"
            ]
            data["gridCumulative"] = data["gridAccounting"]
            _LOGGER.debug(
                "SmartEV grid publication pipeline: stage=coordinator_data "
                "accounting_published_total=%s coordinator_value=%s "
                "same_object=%s",
                data["gridAccounting"].get("total"),
                data["gridCumulative"].get("total"),
                data["gridCumulative"] is data["gridAccounting"],
            )
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
        self, year: int, month: int, today: date
    ) -> tuple[dict, dict, dict, dict | None, dict | None]:
        """Fetch all shared server aggregations without blocking HA."""
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
            if jom_pv_data is not None and today.day <= 2:
                previous_year = year if month > 1 else year - 1
                previous_month = month - 1 if month > 1 else 12
                previous_jom_pv = self.client.get_jom_pv_data(
                    year=previous_year, month=previous_month
                )
                if previous_jom_pv is not None:
                    jom_pv_data["daily"] = {
                        **previous_jom_pv["daily"],
                        **jom_pv_data["daily"],
                    }
        except (requests.RequestException, ValueError) as err:
            _LOGGER.debug("Unable to update optional SmartEV JOM PV data: %s", err)
            jom_pv_data = None
        try:
            current_month_production = self.client.get_production_report(
                year=year, month=month
            )
            daily_pv = current_month_production["pv"]["daily"]
            calibration_daily = dict(daily_pv)
            calibration_daily_grid = dict(
                current_month_production["grid"]["daily"]
            )
            accounting_daily_grid = dict(
                current_month_production["grid"]["daily"]
            )
            latest_daily = self._latest_completed_daily_value(daily_pv, today)

            # At a month boundary, the newest delayed value can still be in
            # the previous month's report. Keep both days available for
            # calibration even after the first current-month row appears.
            if today.day <= 7:
                previous_year = year if month > 1 else year - 1
                previous_month = month - 1 if month > 1 else 12
                try:
                    previous_production = self.client.get_production_report(
                        year=previous_year, month=previous_month
                    )
                    previous_latest = self._latest_completed_daily_value(
                        previous_production["pv"]["daily"], today
                    )
                    latest_daily = max(
                        (
                            value
                            for value in (latest_daily, previous_latest)
                            if value is not None
                        ),
                        default=None,
                    )
                    calibration_daily = {
                        **previous_production["pv"]["daily"],
                        **calibration_daily,
                    }
                    calibration_daily_grid = {
                        **previous_production["grid"]["daily"],
                        **calibration_daily_grid,
                    }
                    accounting_daily_grid = {
                        **previous_production["grid"]["daily"],
                        **accounting_daily_grid,
                    }
                except (requests.RequestException, ValueError) as err:
                    _LOGGER.debug(
                        "Unable to update previous month's SmartEV production data: %s",
                        err,
                    )
            current_month_production["pv"]["latest_daily"] = latest_daily
            current_month_production["pv"]["calibration_daily"] = calibration_daily
            current_month_production["grid"][
                "calibration_daily"
            ] = calibration_daily_grid
            current_month_production["grid"][
                "accounting_daily"
            ] = accounting_daily_grid
        except (requests.RequestException, ValueError) as err:
            _LOGGER.debug("Unable to update optional SmartEV production data: %s", err)
            current_month_production = None
        return (
            data,
            current_year_data,
            current_month_data,
            current_month_production,
            jom_pv_data,
        )

    @staticmethod
    def _latest_completed_daily_value(
        daily_values: dict[str, float], today: date
    ) -> tuple[str, float] | None:
        """Return the newest daily value strictly before the local date."""
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
        """Return an API-provided chart value matching a period index."""
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
        """Return a non-negative consumption-minus-allocation value."""
        if (
            isinstance(consumption, bool)
            or not isinstance(consumption, (int, float))
            or isinstance(pv_allocation, bool)
            or not isinstance(pv_allocation, (int, float))
        ):
            return None
        return max(0.0, float(consumption) - float(pv_allocation))
