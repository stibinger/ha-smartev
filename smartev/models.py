from dataclasses import dataclass


@dataclass
class Meter:
    id: int
    total_energy: float
    unit: str
    last_update: str
    interval: str