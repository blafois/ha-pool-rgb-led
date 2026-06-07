"""Constants for the Pool RGB LED integration."""

from __future__ import annotations

DOMAIN = "pool_rgb_led"

CONF_TARGET_ENTITY = "target_entity"
CONF_KNX_ADDRESS = "knx_address"
CONF_PULSE_MS = "pulse_ms"
CONF_GAP_MS = "gap_ms"
CONF_SETTLE_MS = "settle_ms"

KNX_DOMAIN = "knx"
KNX_SERVICE_SEND = "send"

DEFAULT_PULSE_MS = 400
DEFAULT_GAP_MS = 400
DEFAULT_SETTLE_MS = 1500

COLORS: list[str] = [
    "White",
    "Blue",
    "Blue Lagoon",
    "Cyan",
    "Violet",
    "Magenta",
    "Pink",
    "Red",
    "Orange",
    "Green",
    "Warm White",
]

SEQUENCES: list[str] = [
    "Gradient",
    "Rainbow",
    "Parade",
    "Techno",
    "Horizon",
    "Random",
    "Magic",
]

MODES: list[str] = COLORS + SEQUENCES
TOTAL_MODES = len(MODES)

RESYNC_INDEX = 1

SERVICE_RESYNC = "resync"
SERVICE_SET_MODE = "set_mode"
SERVICE_NEXT = "next"

ATTR_MODE = "mode"
ATTR_INDEX = "index"
ATTR_KIND = "kind"
