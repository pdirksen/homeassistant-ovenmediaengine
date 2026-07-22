"""Config flow for OvenMediaEngine."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    OmeApiClient,
    OmeApiError,
    OmeAuthError,
    OmeConnectionError,
    normalize_base_url,
)
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .coordinator import OmeConfigEntry

_LOGGER = logging.getLogger(__name__)


def _user_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """Build the user/reauth form schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_BASE_URL, default=defaults.get(CONF_BASE_URL, "")
            ): str,
            vol.Required(
                CONF_ACCESS_TOKEN, default=defaults.get(CONF_ACCESS_TOKEN, "")
            ): str,
            vol.Required(
                CONF_VERIFY_SSL,
                default=defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            ): bool,
        }
    )


async def _validate(hass, data: Mapping[str, Any]) -> dict[str, str]:
    """Try to reach the server; return a dict of form errors (empty if OK)."""
    session = async_get_clientsession(
        hass, verify_ssl=data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    )
    api = OmeApiClient(
        session=session,
        base_url=data[CONF_BASE_URL],
        access_token=data[CONF_ACCESS_TOKEN],
        verify_ssl=data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )
    try:
        await api.async_validate()
    except OmeAuthError:
        return {"base": "invalid_auth"}
    except (OmeConnectionError, OmeApiError):
        return {"base": "cannot_connect"}
    except Exception:  # noqa: BLE001 - surface any unexpected failure to the user
        _LOGGER.exception("Unexpected error validating OME connection")
        return {"base": "unknown"}
    return {}


class OmeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the OvenMediaEngine config flow."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            base_url = normalize_base_url(user_input[CONF_BASE_URL])
            user_input[CONF_BASE_URL] = base_url
            await self.async_set_unique_id(base_url)
            self._abort_if_unique_id_configured()
            errors = await _validate(self.hass, user_input)
            if not errors:
                return self.async_create_entry(
                    title=base_url.removeprefix("https://").removeprefix("http://"),
                    data=user_input,
                )
        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication on token failure."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm new credentials."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            merged = {**reauth_entry.data, **user_input}
            errors = await _validate(self.hass, merged)
            if not errors:
                return self.async_update_reload_and_abort(
                    reauth_entry, data=merged
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_user_schema(reauth_entry.data),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: OmeConfigEntry) -> OmeOptionsFlow:
        """Return the options flow."""
        return OmeOptionsFlow()


class OmeOptionsFlow(OptionsFlow):
    """Handle the scan-interval option."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current
                    ): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL)),
                }
            ),
        )
