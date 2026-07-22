# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

"""SmartEV API client."""

import csv
from datetime import UTC, datetime
from io import StringIO
import math
import re
from urllib.parse import urlparse

import requests


_AUTHENTICATION_PATH_NAMES = {"auth", "login", "login.php", "sign-in", "signin"}
_PASSWORD_INPUT_PATTERN = re.compile(
    r"<input\b[^>]*\btype\s*=\s*['\"]?password(?:['\"\s>])",
    re.IGNORECASE,
)


def _is_authentication_response(response: requests.Response) -> bool:
    """Return whether a response contains an authentication page."""
    path_name = (
        urlparse(response.url).path.rstrip("/").rsplit("/", 1)[-1].casefold()
    )

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
        raise SmartEVResponseError(
            "SmartEV response field 'meters' must be a list."
        )

    if len(meters) != 1:
        raise SmartEVResponseError(
            "SmartEV response must contain exactly one meter."
        )

    meter = meters[0]
    if not isinstance(meter, dict):
        raise SmartEVResponseError("SmartEV meter data must be a JSON object.")

    if "id" not in meter:
        raise SmartEVResponseError("SmartEV meter data is missing the 'id' field.")

    value = meter.get("value1")
    if value is not None and (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or isinstance(value, float)
        and not math.isfinite(value)
    ):
        raise SmartEVResponseError(
            "SmartEV meter field 'value1' must be a finite number or null."
        )

    timestamp = meter.get("dt")
    if timestamp is not None and (
        isinstance(timestamp, bool)
        or not isinstance(timestamp, (int, float))
        or isinstance(timestamp, float)
        and not math.isfinite(timestamp)
    ):
        raise SmartEVResponseError(
            "SmartEV meter field 'dt' must be a finite numeric timestamp or null."
        )

    if timestamp is not None:
        try:
            datetime.fromtimestamp(timestamp, UTC)
        except (OSError, OverflowError, ValueError) as err:
            raise SmartEVResponseError(
                "SmartEV meter field 'dt' is outside the supported timestamp range."
            ) from err

    return data


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
            date = datetime.strptime(row[0], "%d.%m.%Y").date()
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

        data = self._get_json(
            "/reports/prehled-vyroby-data.php", action="getJoms"
        )
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
                    if isinstance(building_id, int) and not isinstance(building_id, bool):
                        buildings[building_id] = str(building.get("name") or building_id)

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
