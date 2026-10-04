# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

"""SmartEV API client."""

import csv
import math
import re
from datetime import UTC, datetime
from io import StringIO
from urllib.parse import urlparse

import requests

from .meters import finite_number, meters_by_type, reading_datetime

_AUTHENTICATION_PATH_NAMES = {"auth", "login", "login.php", "sign-in", "signin"}
_PASSWORD_INPUT_PATTERN = re.compile(
    r"<input\b[^>]*\btype\s*=\s*['\"]?password(?:['\"\s>])",
    re.IGNORECASE,
)


def _is_authentication_response(response: requests.Response) -> bool:
    """Return whether a response contains an authentication page."""
    path_name = urlparse(response.url).path.rstrip("/").rsplit("/", 1)[-1].casefold()

    if path_name in _AUTHENTICATION_PATH_NAMES:
        return True

    content_type = response.headers.get("Content-Type", "").casefold()
    return (
        "html" in content_type
        and _PASSWORD_INPUT_PATTERN.search(response.text) is not None
    )


def _validate_flat_info(data: object) -> dict:
    """Validate and return a SmartEV flat information response."""
    if not isinstance(data, dict):
        raise SmartEVResponseError("SmartEV response must be a JSON object.")

    for key in ("buildingName", "number", "meters"):
        if key not in data:
            raise SmartEVResponseError(
                f"SmartEV response is missing the '{key}' field."
            )

    meters = data["meters"]
    if not isinstance(meters, list):
        raise SmartEVResponseError("SmartEV response field 'meters' must be a list.")

    _validate_electricity_meters(meters, live=False)
    return data


def _validate_electricity_meters(meters: list, *, live: bool) -> None:
    """Validate electricity independently from optional water/RTN metadata."""
    for meter in meters_by_type(meters).get(0, []):
        if meter.get("id") is None:
            # The dashboard can include a no-meter placeholder.
            continue
        value = meter.get("value1")
        if (live or value is not None) and finite_number(value) is None:
            raise SmartEVResponseError(
                "SmartEV electricity meter field 'value1' must be finite."
            )
        timestamp = meter.get("dt")
        if (live or timestamp is not None) and reading_datetime(timestamp) is None:
            raise SmartEVResponseError(
                "SmartEV electricity meter field 'dt' must be a valid timestamp."
            )


def _validate_live_flat_info(data: object, flat_id: int) -> dict:
    """Validate and return one flat from a building live-meter response."""
    if not isinstance(data, dict) or not isinstance(data.get("flats"), list):
        raise SmartEVResponseError(
            "SmartEV live building meters response has an invalid structure."
        )
    matches = [
        flat
        for flat in data["flats"]
        if isinstance(flat, dict) and flat.get("id") == flat_id
    ]
    if len(matches) != 1:
        raise SmartEVResponseError(
            "SmartEV live building meters response does not contain exactly "
            "one configured apartment."
        )
    flat = matches[0]
    meters = flat.get("meters")
    if not isinstance(meters, list):
        raise SmartEVResponseError(
            "SmartEV live apartment response must contain a meter list."
        )
    _validate_electricity_meters(meters, live=True)
    return flat


def _parse_production_csv(content: bytes) -> dict:
    """Parse an apartment PV production report CSV response."""
    try:
        # SmartEV currently returns Windows-1250 encoded CSV even though
        # the HTTP Content-Type declares UTF-8.
        rows = list(csv.reader(StringIO(content.decode("cp1250")), delimiter=";"))
    except UnicodeDecodeError as err:
        raise SmartEVResponseError(
            "SmartEV returned an invalid production report encoding."
        ) from err
    except csv.Error as err:
        raise SmartEVResponseError(
            "SmartEV returned an invalid production report CSV."
        ) from err

    header = ["Datum", "Celkem [kWh]", "FVE [kWh]", "Síť [kWh]"]
    try:
        header_index = rows.index(header)
    except ValueError as err:
        raise SmartEVResponseError(
            "SmartEV production report is missing the expected CSV header."
        ) from err

    daily_pv: dict[str, float] = {}
    daily_grid: dict[str, float] = {}
    total_pv: float | None = None
    total_grid: float | None = None
    for row in rows[header_index + 1 :]:
        if len(row) != len(header):
            raise SmartEVResponseError(
                "SmartEV production report contains an invalid CSV row."
            )
        try:
            pv_value = float(row[2].replace(",", "."))
            grid_value = float(row[3].replace(",", "."))
        except ValueError as err:
            raise SmartEVResponseError(
                "SmartEV production report contains an invalid energy value."
            ) from err
        if not math.isfinite(pv_value) or not math.isfinite(grid_value):
            raise SmartEVResponseError(
                "SmartEV production report contains a non-finite energy value."
            )
        if row[0] == "Celkem":
            total_pv = pv_value
            total_grid = grid_value
            continue
        try:
            date = datetime.strptime(row[0], "%d.%m.%Y").replace(tzinfo=UTC).date()
        except ValueError as err:
            raise SmartEVResponseError(
                "SmartEV production report contains an invalid date."
            ) from err
        daily_pv[date.isoformat()] = pv_value
        daily_grid[date.isoformat()] = grid_value

    if total_pv is None or total_grid is None:
        raise SmartEVResponseError(
            "SmartEV production report is missing its total row."
        )

    return {
        "pv": {"total": total_pv, "daily": daily_pv},
        "grid": {"total": total_grid, "daily": daily_grid},
    }


class SmartEVError(requests.RequestException):
    """Base exception for SmartEV client errors."""


class SmartEVAuthenticationError(SmartEVError):
    """Raised when SmartEV rejects the supplied credentials."""


class SmartEVResponseError(SmartEVError):
    """Raised when SmartEV returns an unexpected response."""


class SmartEVClient:
    """Client for communicating with SmartEV."""

    BASE_URL = "https://jom.smartev.cz"
    REQUEST_TIMEOUT = 30.0

    def __init__(self, email: str, password: str, flat_id: int | None = None) -> None:
        self._email = email
        self._password = password
        self._flat_id = flat_id
        self._jom_id: int | None = None
        self.session = requests.Session()

    def login(self) -> bool:
        """Log in to SmartEV."""

        payload = {
            "email": self._email,
            "password": self._password,
            "log_in": "Přihlásit se",
        }

        response = self.session.post(
            self.BASE_URL + "/login.php",
            data=payload,
            allow_redirects=True,
            timeout=self.REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        if urlparse(response.url).path.rstrip("/") == "/login.php":
            raise SmartEVAuthenticationError(
                "SmartEV rejected the supplied credentials."
            )

        return True

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def _get_json(self, endpoint: str, **params) -> object:
        """Return an authenticated JSON response from a SmartEV endpoint."""
        response = self.session.get(
            self.BASE_URL + endpoint,
            params=params,
            timeout=self.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        if _is_authentication_response(response):
            raise SmartEVAuthenticationError("SmartEV authentication has expired.")
        try:
            return response.json()
        except requests.JSONDecodeError as err:
            raise SmartEVResponseError(
                "SmartEV returned an invalid JSON response."
            ) from err

    def _get_production_jom_id(self) -> int:
        """Return the JOM containing the configured apartment."""
        if self._flat_id is None:
            raise ValueError("flat_id is required for production reports.")
        if self._jom_id is not None:
            return self._jom_id

        data = self._get_json("/reports/prehled-vyroby-data.php", action="getJoms")
        if not isinstance(data, list):
            raise SmartEVResponseError(
                "SmartEV production report topology must be a JSON array."
            )

        matches: set[int] = set()
        for operator in data:
            if not isinstance(operator, dict):
                continue
            joms = operator.get("joms", [])
            if not isinstance(joms, list):
                continue
            for jom in joms:
                if not isinstance(jom, dict):
                    continue
                jom_id = jom.get("id")
                if not isinstance(jom_id, int) or isinstance(jom_id, bool):
                    continue
                buildings = jom.get("buildings", [])
                if not isinstance(buildings, list):
                    continue
                for building in buildings:
                    if not isinstance(building, dict):
                        continue
                    flats = building.get("flats", [])
                    if not isinstance(flats, list):
                        continue
                    for flat in flats:
                        if isinstance(flat, dict) and flat.get("id") == self._flat_id:
                            matches.add(jom_id)

        if len(matches) != 1:
            raise SmartEVResponseError(
                "The configured apartment does not map to exactly one production JOM."
            )
        self._jom_id = matches.pop()
        return self._jom_id

    def get_production_report(self, year: int, month: int) -> dict:
        """Return PV production data for the configured apartment and period."""
        if self._flat_id is None:
            raise ValueError("flat_id is required for production reports.")
        response = self.session.get(
            self.BASE_URL + "/reports/prehled-vyroby-data.php",
            params={
                "action": "getReportCsv",
                "jomId": self._get_production_jom_id(),
                "flatId": self._flat_id,
                "month": month,
                "year": year,
            },
            timeout=self.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        if _is_authentication_response(response):
            raise SmartEVAuthenticationError("SmartEV authentication has expired.")
        return _parse_production_csv(response.content)

    def get_jom_pv_data(self, year: int, month: int) -> dict | None:
        """Return the JOM cumulative PV register and daily production."""
        jom_id = self._get_production_jom_id()
        data = self._get_json(
            "/data/jomMetersChart.php",
            jomId=jom_id,
            meterType=1,
            y=year,
            m=month,
            d=0,
        )
        if not isinstance(data, dict) or data.get("id") != jom_id:
            raise SmartEVResponseError(
                "SmartEV JOM PV response has an invalid identity."
            )
        meters = data.get("meters")
        if not isinstance(meters, list):
            raise SmartEVResponseError(
                "SmartEV JOM PV response is missing its meter list."
            )

        pv_meters = [
            meter
            for meter in meters
            if isinstance(meter, dict) and meter.get("type") == 1
        ]
        if not pv_meters:
            return None
        meter = next(
            (item for item in pv_meters if item.get("id") == "sum"),
            pv_meters[0],
        )
        register = meter.get("value1")
        if (
            isinstance(register, bool)
            or not isinstance(register, (int, float))
            or not math.isfinite(register)
        ):
            raise SmartEVResponseError(
                "SmartEV JOM PV register must be a finite number."
            )

        chart_data = meter.get("chartData")
        if not isinstance(chart_data, list):
            raise SmartEVResponseError(
                "SmartEV JOM PV response is missing its daily history."
            )
        daily: dict[str, float] = {}
        for row in chart_data:
            if not isinstance(row, dict):
                continue
            value = row.get("val1")
            day = row.get("idx")
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                continue
            try:
                production_date = datetime(
                    year, month, int(str(day)), tzinfo=UTC
                ).date()
            except (TypeError, ValueError):
                continue
            daily[production_date.isoformat()] = float(value)

        return {
            "jom_id": jom_id,
            "meter_id": meter.get("id"),
            "register": float(register),
            "timestamp": meter.get("dt"),
            "daily": daily,
        }

    def discover_apartments(self) -> list[dict]:
        """Return apartments exposed to the authenticated SmartEV account."""
        topology = self._get_json("/data/userOperatorsBuildings.php")
        if not isinstance(topology, list):
            raise SmartEVResponseError("SmartEV topology must be a JSON array.")

        buildings: dict[int, str] = {}
        for operator in topology:
            if not isinstance(operator, dict):
                continue
            for jom in operator.get("joms", []):
                if not isinstance(jom, dict):
                    continue
                for building in jom.get("buildings", []):
                    if not isinstance(building, dict):
                        continue
                    building_id = building.get("id")
                    if isinstance(building_id, int) and not isinstance(
                        building_id, bool
                    ):
                        buildings[building_id] = str(
                            building.get("name") or building_id
                        )

        apartments: dict[int, dict] = {}
        for building_id, building_name in buildings.items():
            data = self._get_json(
                "/data/buildingFlatsMeters.php", buildingId=building_id
            )
            if not isinstance(data, dict) or not isinstance(data.get("flats"), list):
                raise SmartEVResponseError(
                    "SmartEV building apartments response has an invalid structure."
                )
            for flat in data["flats"]:
                if not isinstance(flat, dict) or flat.get("number") is None:
                    continue
                flat_id = flat.get("id")
                if not isinstance(flat_id, int) or isinstance(flat_id, bool):
                    continue
                apartments[flat_id] = {
                    "flat_id": flat_id,
                    "name": str(flat.get("name") or flat_id).strip(),
                    "number": flat["number"],
                    "building_id": building_id,
                    "building_name": building_name.strip(),
                }
        return sorted(
            apartments.values(),
            key=lambda item: (item["building_name"].casefold(), item["number"]),
        )

    def get_flat_info(
        self,
        year: int = 0,
        month: int = 0,
        day: int = 0,
    ) -> dict:
        """Return SmartEV data for the requested period."""

        if self._flat_id is None:
            raise ValueError("flat_id is required for get_flat_info().")
        data = self._get_json(
            "/data/flatMetersChart.php",
            flatId=self._flat_id,
            y=year,
            m=month,
            d=day,
        )
        return _validate_flat_info(data)

    def get_live_flat_info(self, building_id: int) -> dict:
        """Return the configured apartment's live cumulative meter response."""
        if self._flat_id is None:
            raise ValueError("flat_id is required for get_live_flat_info().")
        data = self._get_json("/data/buildingFlatsMeters.php", buildingId=building_id)
        return _validate_live_flat_info(data, self._flat_id)

    def get_water_heating_state(
        self, *, jom_id: int, building_id: int, flat_name: str
    ) -> dict:
        """Read current water/RTN using the exact discovered dashboard context."""
        if self._flat_id is None:
            raise ValueError("flat_id is required for water/heating state.")
        if (
            isinstance(jom_id, bool)
            or not isinstance(jom_id, int)
            or isinstance(building_id, bool)
            or not isinstance(building_id, int)
            or not isinstance(flat_name, str)
        ):
            raise SmartEVResponseError("SmartEV water/heating context is incomplete.")
        data = self._get_json(
            "/data/waterHeatingMetersState.php",
            action="getWaterHeatingMetersStateData",
            flatId=self._flat_id,
            jomId=jom_id,
            buildingId=building_id,
            flatName=flat_name,
        )
        if not isinstance(data, dict) or not isinstance(
            data.get("currentMetersStateData"), dict
        ):
            raise SmartEVResponseError("SmartEV water/heating response is invalid.")
        return data
