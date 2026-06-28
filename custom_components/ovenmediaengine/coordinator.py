"""DataUpdateCoordinator for OvenMediaEngine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OmeApiClient, OmeAuthError, OmeConnectionError
from .const import (
    DOMAIN,
    KIND_APP,
    KIND_STREAM,
    KIND_VHOST,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class OmeObject:
    """A discoverable OME object (vhost, app or stream)."""

    kind: str
    vhost: str
    app: str | None
    stream: str | None

    @property
    def key(self) -> str:
        """Stable unique key for entities/devices."""
        if self.kind == KIND_VHOST:
            return f"{KIND_VHOST}:{self.vhost}"
        if self.kind == KIND_APP:
            return f"{KIND_APP}:{self.vhost}/{self.app}"
        return f"{KIND_STREAM}:{self.vhost}/{self.app}/{self.stream}"

    @property
    def name(self) -> str:
        """Human-friendly object name."""
        if self.kind == KIND_VHOST:
            return self.vhost
        if self.kind == KIND_APP:
            return f"{self.vhost}/{self.app}"
        return self.stream or ""


type OmeConfigEntry = ConfigEntry[OmeDataUpdateCoordinator]


class OmeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the OME server and caches the full topology + stats."""

    config_entry: OmeConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: OmeConfigEntry,
        api: OmeApiClient,
        scan_interval: int,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the full topology and stats tree."""
        try:
            return await self.api.async_fetch_all()
        except OmeAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except OmeConnectionError as err:
            raise UpdateFailed(str(err)) from err

    # -- helpers used by platforms -------------------------------------------

    def iter_objects(self) -> list[OmeObject]:
        """Return every object currently present in the latest poll."""
        objects: list[OmeObject] = []
        data = self.data or {}
        for vhost, vdata in data.items():
            objects.append(OmeObject(KIND_VHOST, vhost, None, None))
            for app, adata in (vdata.get("apps") or {}).items():
                objects.append(OmeObject(KIND_APP, vhost, app, None))
                for stream in (adata.get("streams") or {}):
                    objects.append(OmeObject(KIND_STREAM, vhost, app, stream))
        return objects

    def get_stats(self, obj: OmeObject) -> dict[str, Any] | None:
        """Return the Metrics dict for ``obj`` or ``None`` if it is gone."""
        data = self.data or {}
        vdata = data.get(obj.vhost)
        if vdata is None:
            return None
        if obj.kind == KIND_VHOST:
            return vdata.get("stats")
        adata = (vdata.get("apps") or {}).get(obj.app)
        if adata is None:
            return None
        if obj.kind == KIND_APP:
            return adata.get("stats")
        return (adata.get("streams") or {}).get(obj.stream)

    def object_exists(self, obj: OmeObject) -> bool:
        """Return whether ``obj`` is present in the latest poll."""
        return self.get_stats(obj) is not None
