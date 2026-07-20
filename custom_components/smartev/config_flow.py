# Copyright (c) 2026 Petr Stibinger
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

from .client import SmartEVAuthenticationError, SmartEVClient, SmartEVResponseError
from .const import CONF_EMAIL, CONF_FLAT_ID, CONF_PASSWORD, DOMAIN

CONF_APARTMENT = "apartment"


async def _async_validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate credentials and access to the selected flat."""
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


def _discover_apartments(email: str, password: str) -> list[dict]:
    """Authenticate and discover selectable apartments."""
    client = SmartEVClient(email=email, password=password)
    try:
        client.login()
        return client.discover_apartments()
    finally:
        client.close()


class SmartEVConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a SmartEV config flow."""

    VERSION = 2

    def __init__(self) -> None:
        self._credentials: dict[str, str] | None = None
        self._apartments: dict[int, dict] = {}

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
            except (requests.ConnectionError, requests.Timeout, SmartEVResponseError):
                errors["base"] = "cannot_connect"
            except requests.HTTPError as err:
                status_code = err.response.status_code if err.response is not None else None
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
            description_placeholders={"email": reauth_entry.data[CONF_EMAIL]},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Authenticate and discover apartments."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                apartments = await self.hass.async_add_executor_job(
                    _discover_apartments,
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                )
            except SmartEVAuthenticationError:
                errors["base"] = "invalid_auth"
            except (requests.ConnectionError, requests.Timeout, SmartEVResponseError):
                errors["base"] = "cannot_connect"
            except requests.HTTPError as err:
                status_code = err.response.status_code if err.response is not None else None
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
                if not apartments:
                    return self.async_abort(reason="no_apartments")
                self._credentials = {
                    CONF_EMAIL: user_input[CONF_EMAIL],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                }
                self._apartments = {item["flat_id"]: item for item in apartments}
                if len(apartments) == 1:
                    return await self._async_create_apartment_entry(
                        apartments[0]["flat_id"]
                    )
                return await self.async_step_apartment()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_apartment(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user select one discovered apartment."""
        if self._credentials is None or not self._apartments:
            return self.async_abort(reason="discovery_expired")
        if user_input is not None:
            flat_id = int(user_input[CONF_APARTMENT])
            if flat_id not in self._apartments:
                return self.async_abort(reason="discovery_expired")
            try:
                await _async_validate_input(
                    self.hass,
                    {**self._credentials, CONF_FLAT_ID: flat_id},
                )
            except SmartEVAuthenticationError:
                return self.async_show_form(
                    step_id="apartment",
                    data_schema=self._apartment_schema(),
                    errors={"base": "invalid_auth"},
                )
            except SmartEVResponseError:
                return self.async_show_form(
                    step_id="apartment",
                    data_schema=self._apartment_schema(),
                    errors={"base": "unsupported_apartment"},
                )
            except (requests.ConnectionError, requests.Timeout):
                return self.async_show_form(
                    step_id="apartment",
                    data_schema=self._apartment_schema(),
                    errors={"base": "cannot_connect"},
                )
            except requests.RequestException:
                return self.async_show_form(
                    step_id="apartment",
                    data_schema=self._apartment_schema(),
                    errors={"base": "unknown"},
                )
            return await self._async_create_apartment_entry(flat_id)

        return self.async_show_form(
            step_id="apartment", data_schema=self._apartment_schema()
        )

    def _apartment_schema(self) -> vol.Schema:
        """Build the discovered-apartment selector schema."""
        language = self.context.get("language") or self.hass.config.language
        prefix = "Byt" if language == "cs" else "Apartment"
        choices = {
            str(item["flat_id"]): f"{prefix} {item['number']} – {item['name']}"
            for item in sorted(
                self._apartments.values(),
                key=lambda apartment: int(apartment["number"]),
            )
        }
        return vol.Schema({vol.Required(CONF_APARTMENT): vol.In(choices)})

    async def _async_create_apartment_entry(self, flat_id: int) -> FlowResult:
        """Create a config entry for one discovered apartment."""
        assert self._credentials is not None
        await self.async_set_unique_id(
            f"{self._credentials[CONF_EMAIL].casefold()}:{flat_id}"
        )
        self._abort_if_unique_id_configured()
        apartment = self._apartments[flat_id]
        return self.async_create_entry(
            title=f"SmartEV – {apartment['name']}",
            data={**self._credentials, CONF_FLAT_ID: flat_id},
        )
