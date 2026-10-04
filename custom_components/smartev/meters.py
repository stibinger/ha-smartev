# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

"""Select SmartEV meter types and normalize confirmed apartment channels."""

import logging
import math
from datetime import UTC, datetime

_LOGGER = logging.getLogger(__name__)

# These are apartment/dashboard types, not the JOM chart's type namespace.
ONLINE_CHANNELS = {3: "cold_water", 4: "hot_water", 5: "heating_rtn"}
_CHANNEL_FIELDS = {"cold_water": "SV", "hot_water": "TUV", "heating_rtn": "RTN"}
_KNOWN_TYPES = {0, 1, 2, *ONLINE_CHANNELS}


def finite_number(value: object) -> int | float | None:
    """Keep zero, but reject booleans, strings, and non-finite numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def reading_datetime(value: object) -> datetime | None:
    """Decode a source timestamp without substituting the HTTP request time."""
    timestamp = finite_number(value)
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(timestamp, UTC)
    except (OSError, OverflowError, ValueError):
        return None


def meters_by_type(meters: list) -> dict[int, list[dict]]:
    """Retain every known meter; do not interpret unknown types or array order."""
    grouped: dict[int, list[dict]] = {}
    for meter in meters:
        if not isinstance(meter, dict):
            _LOGGER.debug("Ignoring a SmartEV meter with an invalid object structure")
            continue
        meter_type = meter.get("type")
        # The dashboard treats legacy null-type electricity as type 0.
        if meter_type is None:
            meter_type = 0
        if (
            isinstance(meter_type, bool)
            or not isinstance(meter_type, int)
            or meter_type not in _KNOWN_TYPES
        ):
            _LOGGER.debug(
                "Ignoring unsupported SmartEV apartment meter type %r", meter_type
            )
            continue
        grouped.setdefault(meter_type, []).append(meter)
    return grouped


def electricity_meter(meters: list, meter_id: object = None) -> dict | None:
    """Select an identified electricity meter, refusing ambiguous collections."""
    candidates = [
        meter
        for meter in meters_by_type(meters).get(0, [])
        if meter.get("id") is not None
        and (meter_id is None or meter.get("id") == meter_id)
    ]
    if len(candidates) > 1:
        raise ValueError("SmartEV apartment electricity meter selection is ambiguous.")
    return next(iter(candidates), None)


def online_channels(grouped: dict[int, list[dict]], response: dict | None) -> dict:
    """Normalize only channels discovered in the apartment's live meter list.

    The waterHeating endpoint can return all-zero placeholders for absent
    channels. Its keys alone are therefore not evidence of installed meters.
    Values come exclusively from currentMetersStateData; value2 is never used.
    """
    current = response.get("currentMetersStateData") if response is not None else None
    if not isinstance(current, dict):
        current = {}
    channels = {}
    for meter_type, key in ONLINE_CHANNELS.items():
        meters = grouped.get(meter_type, [])
        if not meters:
            continue
        value = finite_number(current.get(_CHANNEL_FIELDS[key]))
        if value is not None and meter_type in (3, 4):
            value = value / 1000.0
        # A timestamp cannot be assigned to an aggregate of multiple physical
        # records without documented backend semantics. Keep the value channel.
        meter = next(iter(meters)) if len(meters) == 1 else None
        channels[key] = {
            "value": value,
            "last_reading": reading_datetime(meter.get("dt")) if meter else None,
        }
    return channels
