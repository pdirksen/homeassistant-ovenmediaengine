"""Base entity and device helpers for OvenMediaEngine."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    KIND_APP,
    KIND_STREAM,
    KIND_VHOST,
    MANUFACTURER,
    MODEL_APP,
    MODEL_SERVER,
    MODEL_STREAM,
    MODEL_VHOST,
)
from .coordinator import OmeDataUpdateCoordinator, OmeObject


def _device_id(entry_id: str, key: str) -> str:
    """Build a registry-unique device identifier string."""
    return f"{entry_id}:{key}"


def server_device_info(
    entry_id: str, host: str, port: int
) -> DeviceInfo:
    """DeviceInfo for the top-level server device."""
    return DeviceInfo(
        identifiers={(DOMAIN, _device_id(entry_id, "server"))},
        manufacturer=MANUFACTURER,
        model=MODEL_SERVER,
        name=f"OvenMediaEngine ({host}:{port})",
        configuration_url=f"http://{host}:{port}",
    )


def object_device_info(entry_id: str, host: str, port: int, obj: OmeObject) -> DeviceInfo:
    """Build a DeviceInfo for an OME object, chained via via_device."""
    if obj.kind == KIND_VHOST:
        return DeviceInfo(
            identifiers={(DOMAIN, _device_id(entry_id, obj.key))},
            manufacturer=MANUFACTURER,
            model=MODEL_VHOST,
            name=f"vHost {obj.vhost}",
            via_device=(DOMAIN, _device_id(entry_id, "server")),
        )
    if obj.kind == KIND_APP:
        parent = OmeObject(KIND_VHOST, obj.vhost, None, None)
        return DeviceInfo(
            identifiers={(DOMAIN, _device_id(entry_id, obj.key))},
            manufacturer=MANUFACTURER,
            model=MODEL_APP,
            name=f"App {obj.app}",
            via_device=(DOMAIN, _device_id(entry_id, parent.key)),
        )
    parent = OmeObject(KIND_APP, obj.vhost, obj.app, None)
    return DeviceInfo(
        identifiers={(DOMAIN, _device_id(entry_id, obj.key))},
        manufacturer=MANUFACTURER,
        model=MODEL_STREAM,
        name=f"Stream {obj.stream}",
        via_device=(DOMAIN, _device_id(entry_id, parent.key)),
    )


class OmeEntity(CoordinatorEntity[OmeDataUpdateCoordinator]):
    """Base entity bound to a single OME object."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OmeDataUpdateCoordinator,
        obj: OmeObject,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._obj = obj
        entry = coordinator.config_entry
        host = entry.data["host"]
        port = entry.data["port"]
        self._attr_device_info = object_device_info(
            entry.entry_id, host, port, obj
        )

    @property
    def available(self) -> bool:
        """Entity is available while its object is present in the last poll."""
        return super().available and self.coordinator.object_exists(self._obj)
