# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

"""SmartEV API client."""

from datetime import UTC, datetime
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

    def __init__(self, email: str, password: str, flat_id: int) -> None:
        self._email = email
        self._password = password
        self._flat_id = flat_id
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

    def get_flat_info(
        self,
        year: int = 0,
        month: int = 0,
        day: int = 0,
    ) -> dict:
        """Return SmartEV data for the requested period."""

        response = self.session.get(
            self.BASE_URL + "/data/flatMetersChart.php",
            params={
                "flatId": self._flat_id,
                "y": year,
                "m": month,
                "d": day,
            },
            timeout=self.REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        if _is_authentication_response(response):
            raise SmartEVAuthenticationError("SmartEV authentication has expired.")

        try:
            data = response.json()
        except requests.JSONDecodeError as err:
            raise SmartEVResponseError(
                "SmartEV returned an invalid JSON response."
            ) from err

        return _validate_flat_info(data)
