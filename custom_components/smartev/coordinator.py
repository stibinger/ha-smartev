from datetime import timedelta
import logging

import requests
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import SmartEVAuthenticationError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SmartEVCoordinator(DataUpdateCoordinator[dict]):
    """SmartEV data coordinator."""

    def __init__(self, hass: HomeAssistant, client) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )

        self.client = client

    async def _async_update_data(self):
        """Fetch data from SmartEV."""
        try:
            return await self.hass.async_add_executor_job(self.client.get_flat_info)
        except SmartEVAuthenticationError as err:
            raise ConfigEntryAuthFailed("SmartEV authentication failed") from err
        except requests.HTTPError as err:
            status_code = err.response.status_code if err.response is not None else None

            if status_code in (401, 403):
                raise ConfigEntryAuthFailed("SmartEV authentication failed") from err
            raise UpdateFailed(f"Error communicating with SmartEV: {err}") from err
        except (requests.RequestException, ValueError) as err:
            raise UpdateFailed(f"Error communicating with SmartEV: {err}") from err
