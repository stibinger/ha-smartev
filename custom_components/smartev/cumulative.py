# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

"""Reusable persistent daily-to-cumulative energy counter."""

from __future__ import annotations

from datetime import datetime
import math
from typing import Any


class DailyCumulativeEnergyCounter:
    """Turn a resetting daily value into a monotonic cumulative value."""

    def __init__(self, state: dict[str, Any]) -> None:
        self._state = state

    @staticmethod
    def empty_state() -> dict[str, Any]:
        """Return initial persistent state."""
        return {
            "anchor": 0.0,
            "total": 0.0,
            "today": 0.0,
            "date": None,
            "last_source": None,
            "active_multiplier": None,
            "last_rollover": None,
        }

    def update(
        self,
        now: datetime,
        current_daily: Any,
        daily_history: dict[str, Any] | None = None,
        multiplier: float = 1.0,
    ) -> float | None:
        """Update from a daily source and return its cumulative total."""
        source = self._finite_number(current_daily)
        factor = self._finite_number(multiplier)
        if source is None or source < 0 or factor is None or factor < 0:
            return self.total

        today = now.date().isoformat()
        counter_date = self._state.get("date")
        total = self.total or 0.0
        anchor = self._finite_number(self._state.get("anchor")) or 0.0
        previous_source = self._finite_number(self._state.get("last_source"))
        active_factor = self._finite_number(
            self._state.get("active_multiplier")
        )

        if counter_date is None:
            accumulated_today = source * factor
            anchor = max(anchor, total - accumulated_today, 0.0)
            total = max(total, anchor + accumulated_today)
            self._state.update(
                {
                    "anchor": anchor,
                    "total": total,
                    "today": accumulated_today,
                    "date": today,
                    "last_source": source,
                    "active_multiplier": factor,
                }
            )
            return total

        if counter_date != today:
            accumulated_today = (
                self._finite_number(self._state.get("today")) or 0.0
            )
            final_previous = self._finite_number(
                (daily_history or {}).get(counter_date)
            )
            if (
                final_previous is not None
                and previous_source is not None
                and final_previous >= previous_source
                and active_factor is not None
            ):
                accumulated_today += (
                    final_previous - previous_source
                ) * active_factor

            # The completed day becomes the next day's anchor exactly once,
            # identified by the stored date.
            anchor = max(total, anchor + accumulated_today)
            accumulated_today = source * factor
            total = max(total, anchor + accumulated_today)
            self._state.update(
                {
                    "anchor": anchor,
                    "total": total,
                    "today": accumulated_today,
                    "date": today,
                    "last_source": source,
                    "active_multiplier": factor,
                    "last_rollover": now.isoformat(),
                }
            )
            return total

        accumulated_today = (
            self._finite_number(self._state.get("today")) or 0.0
        )
        source_advanced = (
            previous_source is not None
            and source >= previous_source
            and active_factor is not None
        )
        if source_advanced:
            accumulated_today += (source - previous_source) * active_factor

        total = max(total, anchor + accumulated_today)
        self._state.update(
            {
                "total": total,
                "today": accumulated_today,
                # Ignore a transient decrease completely. Moving the baseline
                # backwards would count the same energy again when it recovers.
                "last_source": source if source_advanced else previous_source,
                # Multiplier changes apply only to future source increments.
                "active_multiplier": factor,
            }
        )
        return total

    @property
    def total(self) -> float | None:
        """Return the last cumulative value."""
        return self._finite_number(self._state.get("total"))

    @property
    def attributes(self) -> dict[str, Any]:
        """Return concise counter diagnostics."""
        return {
            "anchor_value": self._finite_number(self._state.get("anchor")),
            "last_rollover": self._state.get("last_rollover"),
        }

    @staticmethod
    def _finite_number(value: Any) -> float | None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            return None
        return float(value)
