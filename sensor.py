"""Sensor platform for Emax Weather integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_TYPE_HUMIDITY,
    SENSOR_TYPE_LIGHT,
    SENSOR_TYPE_NOISE,
    SENSOR_TYPE_PRESSURE,
    SENSOR_TYPE_RAINFALL,
    SENSOR_TYPE_TEMPERATURE,
    SENSOR_TYPE_WIND_SPEED,
)
from . import EmaxWeatherCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class EmaxSensorDescription(SensorEntityDescription):
    """Description of an Emax sensor."""

    value_fn: Optional[Callable] = None
    sensor_type: Optional[int] = None


SENSOR_DESCRIPTIONS = [
    EmaxSensorDescription(
        key="temperature",
        name="Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        sensor_type=SENSOR_TYPE_TEMPERATURE,
    ),
    EmaxSensorDescription(
        key="humidity",
        name="Humidity",
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        sensor_type=SENSOR_TYPE_HUMIDITY,
    ),
    EmaxSensorDescription(
        key="pressure",
        name="Pressure",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.HPA,
    ),
    EmaxSensorDescription(
        key="wind_speed",
        name="Wind Speed",
        icon="mdi:wind-power",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        sensor_type=SENSOR_TYPE_WIND_SPEED,
    ),
    EmaxSensorDescription(
        key="light",
        name="Light",
        icon="mdi:lightbulb",
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="lux",
        sensor_type=SENSOR_TYPE_LIGHT,
    ),
    EmaxSensorDescription(
        key="noise",
        name="Noise",
        icon="mdi:volume-high",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="dB",
        sensor_type=SENSOR_TYPE_NOISE,
    ),
    EmaxSensorDescription(
        key="rainfall",
        name="Rainfall",
        icon="mdi:weather-rainy",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="mm",
        sensor_type=SENSOR_TYPE_RAINFALL,
    ),
    EmaxSensorDescription(
        key="device_mac",
        name="Device MAC",
        icon="mdi:identifier",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda data: data.get("deviceMac"),
    ),
    EmaxSensorDescription(
        key="update_time",
        name="Last Update",
        icon="mdi:clock",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda data: data.get("updateTime"),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: EmaxWeatherCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    entities = []

    # Discover channels from the latest coordinator data. sensorDatas entries
    # contain a `channel` field for radio channels. According to the device
    # protocol, channel 0 is the internal weather info and channels 1-3 are
    # to be ignored. We create devices/entities for channel 0 and any radio
    # channels >= 4 discovered in the data.
    channels = set()
    data = coordinator.data or {}
    for sensor in data.get("sensorDatas", []):
        try:
            ch = int(sensor.get("channel", -1))
        except (TypeError, ValueError):
            continue
        channels.add(ch)

    # Ensure internal channel 0 is present so main device sensors are added
    channels.add(0)

    # Exclude channels 1-3 as they are development channels that are bugged
    channels = {ch for ch in channels if ch not in (1, 2, 3)}

    # Sort for stable ordering
    for channel in sorted(channels):
        for description in SENSOR_DESCRIPTIONS:
            entities.append(
                EmaxWeatherSensor(
                    coordinator=coordinator,
                    description=description,
                    config_entry=entry,
                    channel=channel,
                )
            )

    async_add_entities(entities)


class EmaxWeatherSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Emax weather sensor."""

    entity_description: EmaxSensorDescription

    def __init__(
        self,
        coordinator: EmaxWeatherCoordinator,
        description: EmaxSensorDescription,
        config_entry: ConfigEntry,
        channel: int = 0,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._config_entry = config_entry
        self._channel = int(channel)
        # Make unique id include config entry id and channel to avoid clashes
        self._attr_unique_id = (
            f"{DOMAIN}_{config_entry.entry_id}_ch{self._channel}_{description.key}"
        )

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        if not self.coordinator.data:
            return None

        data = self.coordinator.data

        # Use custom value function if provided
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(data)

        # Extract from sensor data by type and channel
        if self.entity_description.sensor_type is not None:
            sensors = data.get("sensorDatas", [])
            for sensor in sensors:
                # Filter by type and the configured channel for this entity
                try:
                    sensor_channel = int(sensor.get("channel", -1))
                except (TypeError, ValueError):
                    continue

                if sensor.get("type") != self.entity_description.sensor_type:
                    continue

                # Match sensor to this entity's channel
                if sensor_channel != self._channel:
                    continue

                # It shouldn't be but this is precautionary
                if sensor["channel"] in [1, 2, 3]: continue

                # Extract value safely
                value = sensor.get("curVal")

                # Convert temperature from Fahrenheit to Celsius if needed
                if self.entity_description.key == "temperature" and value is not None:
                    try:
                        # Some devices report Fahrenheit; attempt conversion
                        value = (value - 32) * 5 / 9
                    except Exception:
                        pass

                if self.entity_description.key == "wind_speed":
                    # Wind info is nested
                    value = sensor.get("devWindVal", {}).get("currWindSpeed")
                if value is None:
                    return 0
                return value
            return None

        # Fallback for pressure (if not in sensorDatas)
        if self.entity_description.key == "pressure":
            return data.get("atmos")

        return None

    @property
    def device_info(self):
        """Return device info."""
        user_data = self.coordinator.api_client.user_data or {}
        # Provide channel-specific device identifiers so each radio channel
        # becomes its own device in Home Assistant. Channel 0 is treated as
        # the internal device; other channels will be named accordingly.
        nickname = user_data.get("nickname", "Device")
        model = user_data.get("deviceModel", "Weather Station")

        # Device identifier includes config entry id and channel
        identifiers = {(DOMAIN, f"{self._config_entry.entry_id}_ch{self._channel}")}

        if self._channel == 0:
            name = f"Emax Weather - {nickname} (internal)"
        else:
            name = f"Emax Weather - {nickname} (device ID {self._channel})"

        return {
            "identifiers": identifiers,
            "name": name,
            "manufacturer": "EMAX",
            "model": model,
            "sw_version": user_data.get("deviceVersion", "Unknown"),
        }
