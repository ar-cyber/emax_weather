"""Sensor platform for Emax Weather integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional
import inspect

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
    # Whether this description should be created per radio channel. Set to
    # False for global device-level sensors (deviceMac, updateTime, etc.).
    per_channel: bool = True


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
        # per_channel=True,
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
        # make light a primary sensor (lux)
        per_channel=True,
    ),
    EmaxSensorDescription(
        key="ultraviolet",
        name="Ultraviolet",
        icon="mdi:weather-sunny-alert",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        sensor_type=SENSOR_TYPE_LIGHT,
        per_channel=True,
    ),
    EmaxSensorDescription(
        key="noise",
        name="Noise",
        icon="mdi:volume-high",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="dB",
        sensor_type=SENSOR_TYPE_NOISE,
        # primary sound sensor
        per_channel=True,
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
        per_channel=False,
    ),
    EmaxSensorDescription(
        key="update_time",
        name="Last Update",
        icon="mdi:clock",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda data: data.get("updateTime"),
        per_channel=False,
    ),
]

# Global device-level sensors available from the API
GLOBAL_SENSOR_DESCRIPTIONS = [
    EmaxSensorDescription(
        key="dev_timezone",
        name="Device Timezone",
        icon="mdi:clock-time-four-outline",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda data: data.get("devTimezone"),
        per_channel=False,
    ),
    EmaxSensorDescription(
        key="device_time",
        name="Device Time",
        icon="mdi:clock",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda data: data.get("devTime"),
        per_channel=False,
    ),
    EmaxSensorDescription(
        key="wireless_status",
        name="Wireless Status",
        icon="mdi:wifi",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda data: data.get("wirelessStatus"),
        per_channel=False,
    ),
    EmaxSensorDescription(
        key="power_status",
        name="Power Status",
        icon="mdi:power",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda data: data.get("powerStatus"),
        per_channel=False,
    ),
    EmaxSensorDescription(
        key="weather_status",
        name="Weather Status",
        icon="mdi:weather-partly-cloudy",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda data: data.get("weatherStatus"),
        per_channel=False,
    ),
]

# Per-channel nested sensors (wind stats, rainfall, noise, light)
PER_CHANNEL_EXTRA_DESCRIPTIONS = [
    EmaxSensorDescription(
        key="wind_hour_speed",
        name="Wind Speed (hour)",
        icon="mdi:weather-windy",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        sensor_type=SENSOR_TYPE_WIND_SPEED,
    ),
    EmaxSensorDescription(
        key="wind_day_speed",
        name="Wind Speed (day)",
        icon="mdi:weather-windy",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        sensor_type=SENSOR_TYPE_WIND_SPEED,
    ),
    EmaxSensorDescription(
        key="wind_week_speed",
        name="Wind Speed (week)",
        icon="mdi:weather-windy",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        sensor_type=SENSOR_TYPE_WIND_SPEED,
    ),
    EmaxSensorDescription(
        key="wind_month_speed",
        name="Wind Speed (month)",
        icon="mdi:weather-windy",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        sensor_type=SENSOR_TYPE_WIND_SPEED,
    ),
    EmaxSensorDescription(
        key="wind_year_speed",
        name="Wind Speed (year)",
        icon="mdi:weather-windy",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        sensor_type=SENSOR_TYPE_WIND_SPEED,
    ),
    EmaxSensorDescription(
        key="wind_direction",
        name="Wind Direction",
        icon="mdi:compass",
        device_class=None,
        state_class=None,
        native_unit_of_measurement="°",
        sensor_type=SENSOR_TYPE_WIND_SPEED,
    ),
    EmaxSensorDescription(
        key="rain_month",
        name="Rainfall (month)",
        icon="mdi:weather-rainy",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="mm",
        sensor_type=SENSOR_TYPE_RAINFALL,
    ),
    EmaxSensorDescription(
        key="rain_year",
        name="Rainfall (year)",
        icon="mdi:weather-rainy",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="mm",
        sensor_type=SENSOR_TYPE_RAINFALL,
    ),
    EmaxSensorDescription(
        key="rain_accumulated",
        name="Rainfall (accumulated)",
        icon="mdi:weather-rainy",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="mm",
        sensor_type=SENSOR_TYPE_RAINFALL,
    ),
    EmaxSensorDescription(
        key="noise_hour_max",
        name="Noise Hour Max",
        icon="mdi:volume-high",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="dB",
        sensor_type=SENSOR_TYPE_NOISE,
    ),
    EmaxSensorDescription(
        key="noise_hour_avg",
        name="Noise Hour Avg",
        icon="mdi:volume-medium",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="dB",
        sensor_type=SENSOR_TYPE_NOISE,
    ),
    EmaxSensorDescription(
        key="noise_day_max",
        name="Noise Day Max",
        icon="mdi:volume-high",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="dB",
        sensor_type=SENSOR_TYPE_NOISE,
    ),
    EmaxSensorDescription(
        key="noise_day_avg",
        name="Noise Day Avg",
        icon="mdi:volume-medium",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="dB",
        sensor_type=SENSOR_TYPE_NOISE,
    ),
    EmaxSensorDescription(
        key="light_current",
        name="Light Intensity",
        icon="mdi:lightbulb",
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="lux",
        sensor_type=SENSOR_TYPE_LIGHT,
    ),
    EmaxSensorDescription(
        key="light_hour",
        name="Light Intensity (hour)",
        icon="mdi:lightbulb",
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="lux",
        sensor_type=SENSOR_TYPE_LIGHT,
    ),
    EmaxSensorDescription(
        key="light_max",
        name="Light Intensity Max",
        icon="mdi:lightbulb",
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="lux",
        sensor_type=SENSOR_TYPE_LIGHT,
    ),
    # UV handled as primary 'ultraviolet' sensor above; no extra UV keys here
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
            # If description is not per_channel, skip here
            if getattr(description, "per_channel", True) is False and channel == 0:
                # global-only sensors should NOT be created on channel 0
                continue

            entities.append(
                EmaxWeatherSensor(
                    coordinator=coordinator,
                    description=description,
                    config_entry=entry,
                    channel=channel,
                )
            )

        # Add extra per-channel sensors (wind stats, rainfall, noise, light)
        for extra in PER_CHANNEL_EXTRA_DESCRIPTIONS:
            entities.append(
                EmaxWeatherSensor(
                    coordinator=coordinator,
                    description=extra,
                    config_entry=entry,
                    channel=channel,
                )
            )

    # Add global-only sensors (device-level) once, attached to channel 0 device
    for g in GLOBAL_SENSOR_DESCRIPTIONS:
        entities.append(
            EmaxWeatherSensor(
                coordinator=coordinator,
                description=g,
                config_entry=entry,
                channel=0,
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
            # Special handling for wind data: the device reports wind under
            # devWindVal in a sensor of type SENSOR_TYPE_WIND_SPEED. That
            # sensor may be reported on a different channel (commonly 99).
            # We therefore search all wind sensors and prefer same-channel
            # but fall back to the first available wind sensor.
            key = self.entity_description.key
            if self.entity_description.sensor_type == SENSOR_TYPE_WIND_SPEED or key.startswith("wind_"):
                wind_sensors = [s for s in sensors if s.get("type") == SENSOR_TYPE_WIND_SPEED]
                chosen = None
                # Prefer same-channel wind sensor
                for s in wind_sensors:
                    try:
                        if int(s.get("channel", -1)) == self._channel and not int(s.get("channel", -1)) == 0: # Please note that wind sensors CANNOT be on channel 0
                            chosen = s
                            break
                    except (TypeError, ValueError):
                        continue

                # Otherwise pick the first with devWindVal
                if chosen is None:
                    for s in wind_sensors:
                        if s.get("devWindVal"):
                            chosen = s
                            break

                # If still none, no wind data available
                if not chosen:
                    return None

                dev = chosen.get("devWindVal", {})

                # Map keys
                if key == "wind_speed":
                    # Prefer nested currWindSpeed, fall back to curVal
                    value = dev.get("currWindSpeed") if dev.get("currWindSpeed") is not None else chosen.get("curVal")
                else:
                    mapping = {
                        "wind_hour_speed": "hourWindSpeed",
                        "wind_day_speed": "dayWindSpeed",
                        "wind_week_speed": "weekWindSpeed",
                        "wind_month_speed": "monthWindSpeed",
                        "wind_year_speed": "yearWindSpeed",
                        "wind_direction": "windDirection",
                    }
                    value = dev.get(mapping.get(key))

                # Normalize sentinel/invalid
                if isinstance(value, (int, float)) and value in (65535, 255, 65535.0):
                    return None

                return value

            # Default handling for other sensor types
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
                if sensor["channel"] in [1, 2, 3]:
                    continue

                # Extract value safely
                value = sensor.get("curVal")

                # Convert temperature from Fahrenheit to Celsius if needed
                if self.entity_description.key == "temperature" and value is not None:
                    try:
                        # Some devices report Fahrenheit; attempt conversion
                        value = (value - 32) * 5 / 9
                    except Exception:
                        pass

                # For additional per-channel nested extra sensors, map keys
                key = self.entity_description.key
                if key in ("rain_month", "rain_year", "rain_accumulated"):
                    mapping = {
                        "rain_month": "monthRainfall",
                        "rain_year": "yearRainfall",
                        "rain_accumulated": "accumulateRainfall",
                    }
                    value = sensor.get("devRainfullVals", {}).get(mapping.get(key))

                if key in ("noise_hour_max", "noise_hour_avg", "noise_day_max", "noise_day_avg", "noise"):
                    # Prefer averages when available (hourNoiseAvg/dayNoiseAvg)
                    noise = sensor.get("devNoiseVals", {})
                    if key == "noise":
                        # top-level primary noise: prefer hour avg then day avg then max
                        candidates = [noise.get("hourNoiseAvg"), noise.get("dayNoiseAvg"), noise.get("hourNoiseMax"), noise.get("dayNoiseMax")]
                        # treat sentinel values as None
                        candidates = [None if v in (65535, 255) else v for v in candidates]
                        value = next((v for v in candidates if v is not None), None)
                    else:
                        mapping = {
                            "noise_hour_max": "hourNoiseMax",
                            "noise_hour_avg": "hourNoiseAvg",
                            "noise_day_max": "dayNoiseMax",
                            "noise_day_avg": "dayNoiseAvg",
                        }
                        value = noise.get(mapping.get(key))

                if key in ("light_current", "light_hour", "light_max", "ultraviolet", "light"):
                    light = sensor.get("devLightVals", {})
                    mapping = {
                        "light_current": "currLightIntensity",
                        "light_hour": "hourLightIntensity",
                        "light_max": "lightIntensityMax",
                        "ultraviolet": "currUltraviolet",
                        "light": "currLightIntensity",
                    }
                    value = light.get(mapping.get(key))

                # Normalize sentinel values for availability
                if isinstance(value, (int, float)) and value in (65535, 255, 65535.0):
                    return None

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
