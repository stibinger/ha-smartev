"""SmartEV API client."""

from urllib.parse import urlparse

import requests


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

        try:
            return response.json()
        except requests.JSONDecodeError as err:
            raise SmartEVResponseError(
                "SmartEV returned an invalid JSON response."
            ) from err