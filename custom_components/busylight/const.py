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

# Base effect names (without speed suffix)
EFFECT_OFF = "off"
EFFECT_BLINK = "blink"
EFFECT_RAINBOW = "rainbow"
EFFECT_PULSE = "pulse"
EFFECT_FLASH = "flash"
EFFECT_FLI = "fli"

# Speed options used by the API for every animated effect
SPEED_SLOW = "slow"
SPEED_MEDIUM = "medium"
SPEED_FAST = "fast"

SPEEDS = [SPEED_SLOW, SPEED_MEDIUM, SPEED_FAST]
DEFAULT_EFFECT_SPEED = SPEED_MEDIUM

# Animated effects that accept a speed parameter
BASE_EFFECTS = [
    EFFECT_BLINK,
    EFFECT_RAINBOW,
    EFFECT_PULSE,
    EFFECT_FLASH,
    EFFECT_FLI,
]


def effect_name(effect: str, speed: str) -> str:
    """Build the Home Assistant effect name for an effect/speed combination."""
    if effect == EFFECT_OFF:
        return EFFECT_OFF
    return f"{effect} {speed}"


# Effects exposed to Home Assistant: "off" plus every effect in all three speeds
SUPPORTED_EFFECTS = [EFFECT_OFF] + [
    effect_name(effect, speed) for effect in BASE_EFFECTS for speed in SPEEDS
]


def parse_effect(name: str | None) -> tuple[str, str]:
    """Split an effect name into (base effect, speed).

    Accepts both the generated "<effect> <speed>" names and bare effect names
    (e.g. from automations written before speeds were exposed), defaulting to
    the medium speed the integration used to hardcode.
    """
    if not name or name == EFFECT_OFF:
        return EFFECT_OFF, DEFAULT_EFFECT_SPEED

    for speed in SPEEDS:
        suffix = f" {speed}"
        if name.endswith(suffix):
            base = name[: -len(suffix)].strip()
            if base in BASE_EFFECTS:
                return base, speed

    if name in BASE_EFFECTS:
        return name, DEFAULT_EFFECT_SPEED

    return EFFECT_OFF, DEFAULT_EFFECT_SPEED

CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
