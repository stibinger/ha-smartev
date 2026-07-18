# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

"""Config flow for the SmartEV integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import requests
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .client import (
    SmartEVAuthenticationError,
    SmartEVClient,
    SmartEVResponseError,
)

from .const import CONF_EMAIL, CONF_FLAT_ID, CONF_PASSWORD, DOMAIN


async def _async_validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> None:
    """Validate credentials and flat access."""
    client = SmartEVClient(
        email=data[CONF_EMAIL],
        password=data[CONF_PASSWORD],
        flat_id=data[CONF_FLAT_ID],
    )

    await hass.async_add_executor_job(_validate_client, client)


def _validate_client(client: SmartEVClient) -> None:
    """Run blocking client validation."""
    try:
        client.login()
        client.get_flat_info()
    finally:
        client.close()


class SmartEVConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartEV."""

    VERSION = 1

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> FlowResult:
        """Start reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm SmartEV reauthentication."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            validation_data = {
                CONF_EMAIL: reauth_entry.data[CONF_EMAIL],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_FLAT_ID: reauth_entry.data[CONF_FLAT_ID],
            }

            try:
                await _async_validate_input(self.hass, validation_data)
            except SmartEVAuthenticationError:
                errors["base"] = "invalid_auth"
            except (
                requests.ConnectionError,
                requests.Timeout,
                SmartEVResponseError,
            ):
                errors["base"] = "cannot_connect"
            except requests.HTTPError as err:
                status_code = (
                    err.response.status_code if err.response is not None else None
                )

                if status_code in (401, 403):
                    errors["base"] = "invalid_auth"
                elif status_code == 429 or (
                    status_code is not None and status_code >= 500
                ):
                    errors["base"] = "cannot_connect"
                else:
                    errors["base"] = "unknown"
            except requests.RequestException:
                errors["base"] = "cannot_connect"
            except (KeyError, ValueError):
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={
                "email": reauth_entry.data[CONF_EMAIL],
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _async_validate_input(self.hass, user_input)
            except SmartEVAuthenticationError:
                errors["base"] = "invalid_auth"
            except (
                requests.ConnectionError,
                requests.Timeout,
                SmartEVResponseError,
            ):
                errors["base"] = "cannot_connect"
            except requests.HTTPError as err:
                status_code = (
                    err.response.status_code if err.response is not None else None
                )

                if status_code in (401, 403):
                    errors["base"] = "invalid_auth"
                elif status_code == 429 or (
                    status_code is not None and status_code >= 500
                ):
                    errors["base"] = "cannot_connect"
                else:
                    errors["base"] = "unknown"
            except requests.RequestException:
                errors["base"] = "cannot_connect"
            except (KeyError, ValueError):
                errors["base"] = "unknown"
            else:
                unique_id = (
                    f"{user_input[CONF_EMAIL].casefold()}:"
                    f"{user_input[CONF_FLAT_ID]}"
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"SmartEV {user_input[CONF_FLAT_ID]}",
                    data=user_input,
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_FLAT_ID): vol.Coerce(int),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
