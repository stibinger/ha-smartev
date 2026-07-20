# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

"""SmartEV Home Assistant integration."""

from __future__ import annotations

import logging

import requests
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)

from .client import (
    SmartEVAuthenticationError,
    SmartEVClient,
    SmartEVResponseError,
)

from .const import CONF_EMAIL, CONF_FLAT_ID, CONF_PASSWORD, DOMAIN
from .coordinator import SmartEVCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate existing flat-based entries to the discovery flow version."""
    if entry.version < 2:
        if CONF_FLAT_ID not in entry.data:
            return False
        hass.config_entries.async_update_entry(entry, version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SmartEV from a config entry."""
    client = SmartEVClient(
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        flat_id=entry.data[CONF_FLAT_ID],
    )

    try:
        try:
            await hass.async_add_executor_job(client.login)
        except SmartEVAuthenticationError as err:
            raise ConfigEntryAuthFailed("Invalid SmartEV credentials") from err
        except (
            requests.ConnectionError,
            requests.Timeout,
            SmartEVResponseError,
        ) as err:
            raise ConfigEntryNotReady(f"Unable to connect to SmartEV: {err}") from err
        except requests.HTTPError as err:
            status_code = err.response.status_code if err.response is not None else None

            if status_code in (401, 403):
                raise ConfigEntryAuthFailed("Invalid SmartEV credentials") from err
            if status_code == 429 or (
                status_code is not None and status_code >= 500
            ):
                raise ConfigEntryNotReady(
                    f"SmartEV is temporarily unavailable: {err}"
                ) from err
            raise ConfigEntryError(f"SmartEV request failed: {err}") from err
        except requests.RequestException as err:
            raise ConfigEntryNotReady(
                f"Unable to connect to SmartEV: {err}"
            ) from err

        coordinator = SmartEVCoordinator(hass, client)
        await coordinator.async_config_entry_first_refresh()

        entry.runtime_data = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        client.close()
        raise

    entry.async_on_unload(client.close)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a SmartEV config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    return unload_ok
