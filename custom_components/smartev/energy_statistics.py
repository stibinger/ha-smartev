# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

"""Authoritative SmartEV completed-day statistics for the Energy Dashboard."""

from __future__ import annotations

from datetime import date, datetime, time
import logging
import math
from typing import Any

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

GRID_STATISTIC_PREFIX = "grid_import"
PV_STATISTIC_PREFIX = "pv_production"


def statistic_id(flat_id: int, kind: str) -> str:
    """Return a stable external statistic ID for one apartment."""
    return f"{DOMAIN}:{kind}_flat_{flat_id}"


def async_publish_completed_day_statistics(
    hass: HomeAssistant,
    flat_id: int,
    today: date,
    grid_daily: dict[str, Any],
    pv_daily: dict[str, Any],
) -> None:
    """Backfill/update authoritative daily SmartEV statistics.

    Each completed calendar day is written at 23:00 local time.  ``sum`` is a
    cumulative year-to-date value, so Home Assistant's daily ``change`` equals
    exactly the SmartEV CSV value for that calendar day. Re-importing the same
    timestamp updates corrections instead of duplicating energy.
    """
    _publish_one(
        hass,
        statistic_id(flat_id, GRID_STATISTIC_PREFIX),
        "SmartEV grid import",
        today,
        grid_daily,
    )
    _publish_one(
        hass,
        statistic_id(flat_id, PV_STATISTIC_PREFIX),
        "SmartEV PV production",
        today,
        pv_daily,
    )


def _publish_one(
    hass: HomeAssistant,
    stat_id: str,
    name: str,
    today: date,
    daily: dict[str, Any],
) -> None:
    parsed: list[tuple[date, float]] = []
    for raw_date, raw_value in daily.items():
        try:
            day = date.fromisoformat(raw_date)
        except (TypeError, ValueError):
            continue
        if day >= today or isinstance(raw_value, bool) or not isinstance(
            raw_value, (int, float)
        ):
            continue
        value = float(raw_value)
        if not math.isfinite(value) or value < 0:
            continue
        parsed.append((day, value))

    if not parsed:
        return

    parsed.sort()
    cumulative = 0.0
    statistics: list[StatisticData] = []
    local_tz = dt_util.get_default_time_zone()
    for day, value in parsed:
        cumulative += value
        statistics.append(
            StatisticData(
                start=datetime.combine(day, time(hour=23), tzinfo=local_tz),
                state=cumulative,
                sum=cumulative,
            )
        )

    metadata = StatisticMetaData(
        mean_type=StatisticMeanType.NONE,
        has_sum=True,
        name=name,
        source=DOMAIN,
        statistic_id=stat_id,
        unit_class="energy",
        unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    )
    async_add_external_statistics(hass, metadata, statistics)
    _LOGGER.debug("Published %d completed SmartEV days to %s", len(statistics), stat_id)
