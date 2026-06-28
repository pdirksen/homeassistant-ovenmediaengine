"""The OvenMediaEngine integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OmeApiClient
from .entity import server_device_info
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USE_TLS,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_TLS,
    DEFAULT_VERIFY_SSL,
)
from .coordinator import OmeConfigEntry, OmeDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: OmeConfigEntry) -> bool:
    """Set up OvenMediaEngine from a config entry."""
    session = async_get_clientsession(
        hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    )
    api = OmeApiClient(
        session=session,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        use_tls=entry.data.get(CONF_USE_TLS, DEFAULT_USE_TLS),
        access_token=entry.data[CONF_ACCESS_TOKEN],
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = OmeDataUpdateCoordinator(hass, entry, api, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Register the top-level server device so child vhost/app/stream devices
    # (which point at it via via_device) have a valid parent.
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        **server_device_info(
            entry.entry_id, entry.data[CONF_HOST], entry.data[CONF_PORT]
        ),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OmeConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: OmeConfigEntry) -> None:
    """Reload the entry when options change (e.g. scan interval)."""
    await hass.config_entries.async_reload(entry.entry_id)
