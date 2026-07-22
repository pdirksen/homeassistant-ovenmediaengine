"""The OvenMediaEngine integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OmeApiClient, normalize_base_url
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_BASE_URL,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USE_TLS,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
)
from .coordinator import OmeConfigEntry, OmeDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: OmeConfigEntry) -> bool:
    """Migrate old config entries (host/port/use_tls -> base_url)."""
    if entry.version > 2:
        # Downgrade from a future version; nothing we can do.
        return False
    if entry.version == 1:
        data = dict(entry.data)
        scheme = "https" if data.pop(CONF_USE_TLS, False) else "http"
        host = data.pop(CONF_HOST)
        port = data.pop(CONF_PORT)
        data[CONF_BASE_URL] = normalize_base_url(f"{scheme}://{host}:{port}")
        hass.config_entries.async_update_entry(
            entry, data=data, version=2, unique_id=data[CONF_BASE_URL]
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: OmeConfigEntry) -> bool:
    """Set up OvenMediaEngine from a config entry."""
    session = async_get_clientsession(
        hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    )
    api = OmeApiClient(
        session=session,
        base_url=entry.data[CONF_BASE_URL],
        access_token=entry.data[CONF_ACCESS_TOKEN],
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = OmeDataUpdateCoordinator(hass, entry, api, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OmeConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: OmeConfigEntry) -> None:
    """Reload the entry when options change (e.g. scan interval)."""
    await hass.config_entries.async_reload(entry.entry_id)
