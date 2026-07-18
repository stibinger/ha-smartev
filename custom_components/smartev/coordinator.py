# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

from datetime import timedelta
import logging

import requests
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .client import SmartEVAuthenticationError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SmartEVCoordinator(DataUpdateCoordinator[dict]):
    """SmartEV data coordinator."""

    def __init__(self, hass: HomeAssistant, client) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )

        self.client = client

    async def _async_update_data(self):
        """Fetch data from SmartEV."""
        try:
            now = dt_util.now()
            data, current_year_data, current_month_data = (
                await self.hass.async_add_executor_job(
                    self._get_consumption_data, now.year, now.month
                )
            )

            data["currentYearConsumption"] = self._period_value(data, now.year)
            data["currentMonthConsumption"] = self._period_value(
                current_year_data, now.month
            )
            data["todayConsumption"] = self._period_value(
                current_month_data, now.day
            )
            data["dailyAggregation"] = current_month_data
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
        self, year: int, month: int
    ) -> tuple[dict, dict, dict]:
        """Fetch all shared server aggregations without blocking HA."""
        return (
            self.client.get_flat_info(),
            self.client.get_flat_info(year=year),
            self.client.get_flat_info(year=year, month=month),
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
