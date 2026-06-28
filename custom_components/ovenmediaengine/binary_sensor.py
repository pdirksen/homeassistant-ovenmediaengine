"""Binary sensor platform for OvenMediaEngine (per-stream online state)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import KIND_STREAM
from .coordinator import OmeConfigEntry, OmeDataUpdateCoordinator, OmeObject
from .entity import OmeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OmeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up an 'online' binary sensor per stream, discovered dynamically."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new_entities: list[OmeStreamOnlineBinarySensor] = []
        for obj in coordinator.iter_objects():
            if obj.kind != KIND_STREAM or obj.key in known:
                continue
            known.add(obj.key)
            new_entities.append(OmeStreamOnlineBinarySensor(coordinator, obj))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_add_new))
    _add_new()


class OmeStreamOnlineBinarySensor(OmeEntity, BinarySensorEntity):
    """True while the stream is present in the latest poll."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "Online"

    def __init__(
        self,
        coordinator: OmeDataUpdateCoordinator,
        obj: OmeObject,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator, obj)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{obj.key}_online"
        )

    @property
    def available(self) -> bool:
        """Always available so 'offline' can be reported when the stream is gone."""
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        """Return whether the stream currently exists on the server."""
        return self.coordinator.object_exists(self._obj)
