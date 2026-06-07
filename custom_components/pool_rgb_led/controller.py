"""Controller that drives the pool RGB LED via power-cycle pulses."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    CONF_GAP_MS,
    CONF_KNX_ADDRESS,
    CONF_PULSE_MS,
    CONF_SETTLE_MS,
    CONF_TARGET_ENTITY,
    DEFAULT_GAP_MS,
    DEFAULT_PULSE_MS,
    DEFAULT_SETTLE_MS,
    DOMAIN,
    KNX_DOMAIN,
    KNX_SERVICE_SEND,
    MODES,
    RESYNC_INDEX,
    TOTAL_MODES,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


class PoolRGBController:
    """Owns the target relay/light, current mode, and the pulse pump."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._index: int = 0
        self._is_on: bool = False
        self._lock = asyncio.Lock()
        self._listeners: list[Callable[[], None]] = []

    @property
    def target_entity(self) -> str | None:
        return self._opt(CONF_TARGET_ENTITY)

    @property
    def knx_address(self) -> str | None:
        addr = self._opt(CONF_KNX_ADDRESS)
        return addr.strip() if isinstance(addr, str) and addr.strip() else None

    @property
    def pulse_ms(self) -> int:
        return int(self._opt(CONF_PULSE_MS, DEFAULT_PULSE_MS))

    @property
    def gap_ms(self) -> int:
        return int(self._opt(CONF_GAP_MS, DEFAULT_GAP_MS))

    @property
    def settle_ms(self) -> int:
        return int(self._opt(CONF_SETTLE_MS, DEFAULT_SETTLE_MS))

    @property
    def index(self) -> int:
        return self._index

    @property
    def mode(self) -> str:
        return MODES[self._index]

    @property
    def is_on(self) -> bool:
        return self._is_on

    def _opt(self, key: str, default: Any = None) -> Any:
        if key in self.entry.options:
            return self.entry.options[key]
        return self.entry.data.get(key, default)

    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(cb)

        def _remove() -> None:
            if cb in self._listeners:
                self._listeners.remove(cb)

        return _remove

    def _notify(self) -> None:
        for cb in list(self._listeners):
            cb()

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self._index = int(data.get("index", 0)) % TOTAL_MODES
        self._is_on = bool(data.get("is_on", False))

    async def _async_save(self) -> None:
        await self._store.async_save({"index": self._index, "is_on": self._is_on})

    async def async_turn_on(self) -> None:
        """Power up the relay; mode stays where it was."""
        async with self._lock:
            await self._relay_on()
            self._is_on = True
            await self._async_save()
            self._notify()

    async def async_turn_off(self) -> None:
        """Power down the relay."""
        async with self._lock:
            await self._relay_off()
            self._is_on = False
            await self._async_save()
            self._notify()

    async def async_next(self) -> None:
        """Advance one mode forward via a single short pulse."""
        async with self._lock:
            await self._ensure_on_locked()
            await self._pulse_forward(1)
            await self._async_save()
            self._notify()

    async def async_set_mode(self, mode: str) -> None:
        """Move to a named mode by stepping forward (cycle is circular)."""
        try:
            target = MODES.index(mode)
        except ValueError as err:
            raise ValueError(f"Unknown mode: {mode}") from err
        async with self._lock:
            await self._ensure_on_locked()
            steps = (target - self._index) % TOTAL_MODES
            if steps == 0:
                self._notify()
                return
            await self._pulse_forward(steps)
            await self._async_save()
            self._notify()

    async def async_resync(self) -> None:
        """Double-pulse to reset the controller; lands on BLUE (index 1)."""
        async with self._lock:
            await self._relay_on()
            await asyncio.sleep(self.settle_ms / 1000)

            # Two short power cuts within the resync window.
            await self._relay_off()
            await asyncio.sleep(self.pulse_ms / 1000)
            await self._relay_on()
            await asyncio.sleep(self.gap_ms / 1000)
            await self._relay_off()
            await asyncio.sleep(self.pulse_ms / 1000)
            await self._relay_on()
            await asyncio.sleep(self.settle_ms / 1000)

            self._index = RESYNC_INDEX
            self._is_on = True
            await self._async_save()
            self._notify()

    async def _ensure_on_locked(self) -> None:
        """Ensure relay is on and lamp settled. Caller holds the lock."""
        if not self._is_on:
            await self._relay_on()
            await asyncio.sleep(self.settle_ms / 1000)
            self._is_on = True

    async def _pulse_forward(self, steps: int) -> None:
        """Cut and restore power `steps` times to advance the mode."""
        for _ in range(steps):
            await self._relay_off()
            await asyncio.sleep(self.pulse_ms / 1000)
            await self._relay_on()
            # Wait long enough for the lamp to register the new mode before
            # another pulse, but short enough not to feel laggy.
            await asyncio.sleep(self.gap_ms / 1000)
            self._index = (self._index + 1) % TOTAL_MODES
        # Final settle so the next call doesn't race the lamp.
        await asyncio.sleep(self.settle_ms / 1000)

    async def _relay_on(self) -> None:
        await self._drive(True)

    async def _relay_off(self) -> None:
        await self._drive(False)

    async def _drive(self, powered: bool) -> None:
        """Send the power command via KNX direct-write or the entity service."""
        knx_addr = self.knx_address
        if knx_addr is not None:
            await self.hass.services.async_call(
                KNX_DOMAIN,
                KNX_SERVICE_SEND,
                {"address": knx_addr, "payload": powered, "response": False},
                blocking=True,
            )
            return

        entity_id = self.target_entity
        if not entity_id:
            raise RuntimeError(
                "Pool RGB LED has neither a target entity nor a KNX address configured"
            )
        domain = entity_id.split(".", 1)[0]
        if domain not in ("light", "switch", "input_boolean"):
            _LOGGER.warning(
                "Pool RGB LED target %s is in domain %s; expected light/switch/input_boolean",
                entity_id,
                domain,
            )
            domain = "homeassistant"
        await self.hass.services.async_call(
            domain,
            SERVICE_TURN_ON if powered else SERVICE_TURN_OFF,
            {"entity_id": entity_id},
            blocking=True,
        )
