from dataclasses import dataclass


@dataclass
class Meter:
    id: int
    total_energy: float
    unit: str
    last_update: str
    interval: str
    current_month_consumption: float | None = None
    current_year_consumption: float | None = None
    today_consumption: float | None = None
