"""Constants for Emax Weather integration."""

DOMAIN = "emax_weather"
SCAN_INTERVAL = 10  # minutes

# Default values
DEFAULT_BASE_URL = "https://app.emaxlife.net/V1.0"
DEFAULT_TIMEOUT = 10

# MD5 Salt for password hashing
PASSWORD_SALT = "emax@pwd123"

# Sensor type constants
SENSOR_TYPE_TEMPERATURE = 1
SENSOR_TYPE_HUMIDITY = 2
SENSOR_TYPE_PRESSURE = 7
SENSOR_TYPE_WIND_SPEED = 3
SENSOR_TYPE_LIGHT = 6
SENSOR_TYPE_NOISE = 5
SENSOR_TYPE_RAINFALL = 4

# Unit mappings
TEMPERATURE_UNIT = "°C"
HUMIDITY_UNIT = "%"
PRESSURE_UNIT = "hPa"
WIND_SPEED_UNIT = "m/s"
LIGHT_UNIT = "lux"
NOISE_UNIT = "dB"
RAINFALL_UNIT = "mm"

# Update events
SERVICE_REFRESH = "refresh"
