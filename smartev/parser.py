from smartev.models import Meter


def _period_value(data: dict | None, index: int) -> float | None:
    """Return a server-provided chart value for a period."""
    if not data:
        return None

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


def parse_meter(
    data: dict,
    *,
    year: int | None = None,
    month: int | None = None,
    current_year_data: dict | None = None,
) -> Meter:
    """Parse meter data, including optional server-provided period totals."""

    meter = data["meters"][0]

    return Meter(
        id=meter["id"],
        total_energy=meter["value1"],
        unit=meter["unit"],
        last_update=meter["dtStr"],
        interval=meter["chartInterval"],
        current_month_consumption=(
            _period_value(current_year_data, month) if month is not None else None
        ),
        current_year_consumption=(
            _period_value(data, year) if year is not None else None
        ),
    )
