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
# FLI ("GetFlashyIndication") alternates two colors and is served by the v1
# flash endpoint; the deprecated GET /light/{id}/fli route is not used.
EFFECT_FLI_PATH = f"{API_PREFIX}/effects/{{light_id}}/flash"
SYSTEM_HEALTH_PATH = f"{API_PREFIX}/system/health"

# Base effect names (without speed suffix)
EFFECT_OFF = "off"
EFFECT_BLINK = "blink"
EFFECT_RAINBOW = "rainbow"
EFFECT_PULSE = "pulse"
EFFECT_FLI = "fli"

# Display names shown in the Home Assistant effect picker
EFFECT_LABELS = {
    EFFECT_FLI: "Police Flash (fli)",
}

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
    EFFECT_FLI,
]


def effect_label(effect: str) -> str:
    """Return the display name of a base effect."""
    return EFFECT_LABELS.get(effect, effect)


def effect_name(effect: str, speed: str) -> str:
    """Build the Home Assistant effect name for an effect/speed combination."""
    if effect == EFFECT_OFF:
        return EFFECT_OFF
    return f"{effect_label(effect)} {speed}"


# Effects exposed to Home Assistant: "off" plus every effect in all three speeds
SUPPORTED_EFFECTS = [EFFECT_OFF] + [
    effect_name(effect, speed) for effect in BASE_EFFECTS for speed in SPEEDS
]


def _build_effect_lookup() -> dict[str, tuple[str, str]]:
    """Map every accepted effect name to its (base effect, speed) pair.

    Keys are lower-cased so the lookup is case-insensitive. Besides the
    generated display names, older/internal spellings such as "fli slow" or a
    bare "rainbow" are accepted so existing automations keep working.
    """
    lookup: dict[str, tuple[str, str]] = {
        EFFECT_OFF: (EFFECT_OFF, DEFAULT_EFFECT_SPEED),
    }
    for effect in BASE_EFFECTS:
        for speed in SPEEDS:
            lookup[effect_name(effect, speed).lower()] = (effect, speed)
            lookup[f"{effect} {speed}".lower()] = (effect, speed)
        lookup[effect.lower()] = (effect, DEFAULT_EFFECT_SPEED)
        lookup[effect_label(effect).lower()] = (effect, DEFAULT_EFFECT_SPEED)
    return lookup


_EFFECT_LOOKUP = _build_effect_lookup()


def parse_effect(name: str | None) -> tuple[str, str]:
    """Split an effect name into (base effect, speed).

    Unknown or missing names resolve to a solid color ("off"); names given
    without a speed fall back to the medium speed the integration used to
    hardcode.
    """
    if not name:
        return EFFECT_OFF, DEFAULT_EFFECT_SPEED

    return _EFFECT_LOOKUP.get(name.strip().lower(), (EFFECT_OFF, DEFAULT_EFFECT_SPEED))

CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
