"""Constants for the Busylight for Humans integration."""

DOMAIN = "busylight"

# Default values
DEFAULT_PORT = 8000
DEFAULT_SCAN_INTERVAL = 10  # seconds

# API paths (v1 preferred)
API_PREFIX = "/api/v1"
LIGHTS_PATH = f"{API_PREFIX}/lights"
LIGHT_STATUS_PATH = f"{API_PREFIX}/lights/{{light_id}}/status"
LIGHT_ON_PATH = f"{API_PREFIX}/lights/{{light_id}}/on"
LIGHT_OFF_PATH = f"{API_PREFIX}/lights/{{light_id}}/off"
LIGHT_BLINK_PATH = f"{API_PREFIX}/lights/{{light_id}}/blink"
EFFECT_RAINBOW_PATH = f"{API_PREFIX}/effects/{{light_id}}/rainbow"
EFFECT_PULSE_PATH = f"{API_PREFIX}/effects/{{light_id}}/pulse"
EFFECT_FLASH_PATH = f"{API_PREFIX}/effects/{{light_id}}/flash"
SYSTEM_HEALTH_PATH = f"{API_PREFIX}/system/health"

# Compatibility / legacy effect path (GET)
EFFECT_FLI_PATH = "/light/{light_id}/fli"

# Effect names exposed to Home Assistant
EFFECT_OFF = "off"
EFFECT_BLINK = "blink"
EFFECT_RAINBOW = "rainbow"
EFFECT_PULSE = "pulse"
EFFECT_FLASH = "flash"
EFFECT_FLI = "fli"

SUPPORTED_EFFECTS = [
    EFFECT_OFF,
    EFFECT_BLINK,
    EFFECT_RAINBOW,
    EFFECT_PULSE,
    EFFECT_FLASH,
    EFFECT_FLI,
]

# Speed options used by the API
SPEED_SLOW = "slow"
SPEED_MEDIUM = "medium"
SPEED_FAST = "fast"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
