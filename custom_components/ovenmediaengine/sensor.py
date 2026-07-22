"""Sensor platform for OvenMediaEngine."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfDataRate, UnitOfInformation
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONNECTION_PROTOCOLS
from .coordinator import OmeConfigEntry, OmeDataUpdateCoordinator, OmeObject
from .entity import OmeEntity


@dataclass(frozen=True, kw_only=True)
class OmeSensorEntityDescription(SensorEntityDescription):
    """Describes an OME metric sensor."""

    value_fn: Callable[[Mapping[str, Any]], Any]
    attr_fn: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None


SENSORS: tuple[OmeSensorEntityDescription, ...] = (
    OmeSensorEntityDescription(
        key="total_connections",
        name="Total connections",
        icon="mdi:account-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda m: m.get("totalConnections"),
        attr_fn=lambda m: {
            proto: (m.get("connections") or {}).get(proto, 0)
            for proto in CONNECTION_PROTOCOLS
        },
    ),
    OmeSensorEntityDescription(
        key="max_total_connections",
        name="Max total connections",
        icon="mdi:account-multiple-plus",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda m: m.get("maxTotalConnections"),
    ),
    OmeSensorEntityDescription(
        key="last_throughput_in",
        name="Throughput in",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.BITS_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda m: m.get("lastThroughputIn"),
    ),
    OmeSensorEntityDescription(
        key="avg_throughput_in",
        name="Average throughput in",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.BITS_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda m: m.get("avgThroughputIn"),
    ),
    OmeSensorEntityDescription(
        key="avg_throughput_out",
        name="Average throughput out",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.BITS_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda m: m.get("avgThroughputOut"),
    ),
    OmeSensorEntityDescription(
        key="max_throughput_in",
        name="Max throughput in",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.BITS_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda m: m.get("maxThroughputIn"),
    ),
    OmeSensorEntityDescription(
        key="max_throughput_out",
        name="Max throughput out",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.BITS_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda m: m.get("maxThroughputOut"),
    ),
    OmeSensorEntityDescription(
        key="total_bytes_in",
        name="Total bytes in",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda m: m.get("totalBytesIn"),
    ),
    OmeSensorEntityDescription(
        key="total_bytes_out",
        name="Total bytes out",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda m: m.get("totalBytesOut"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OmeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors, adding new objects as they are discovered."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new_entities: list[OmeSensor] = []
        for obj in coordinator.iter_objects():
            for description in SENSORS:
                uid = f"{obj.key}_{description.key}"
                if uid in known:
                    continue
                known.add(uid)
                new_entities.append(OmeSensor(coordinator, obj, description))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_add_new))
    _add_new()


class OmeSensor(OmeEntity, SensorEntity):
    """A single OME metric sensor."""

    entity_description: OmeSensorEntityDescription

    def __init__(
        self,
        coordinator: OmeDataUpdateCoordinator,
        obj: OmeObject,
        description: OmeSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, obj)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{obj.key}_{description.key}"
        )

    @property
    def native_value(self) -> Any:
        """Return the metric value."""
        stats = self.coordinator.get_stats(self._obj)
        if stats is None:
            return None
        return self.entity_description.value_fn(stats)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return per-protocol connection counts where applicable."""
        if self.entity_description.attr_fn is None:
            return None
        stats = self.coordinator.get_stats(self._obj)
        if stats is None:
            return None
        return dict(self.entity_description.attr_fn(stats))
