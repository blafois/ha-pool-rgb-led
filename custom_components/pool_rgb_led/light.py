"""Light entity that fronts the pool RGB LED controller."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import voluptuous as vol

from .const import (
    ATTR_INDEX,
    ATTR_KIND,
    ATTR_MODE,
    COLORS,
    DOMAIN,
    MODES,
    SEQUENCES,
    SERVICE_NEXT,
    SERVICE_RESYNC,
    SERVICE_SET_MODE,
)
from .controller import PoolRGBController


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    controller: PoolRGBController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PoolRGBLight(controller, entry)])

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_RESYNC,
        {},
        "async_service_resync",
    )
    platform.async_register_entity_service(
        SERVICE_NEXT,
        {},
        "async_service_next",
    )
    platform.async_register_entity_service(
        SERVICE_SET_MODE,
        {vol.Required(ATTR_MODE): vol.In(MODES)},
        "async_service_set_mode",
    )


class PoolRGBLight(LightEntity):
    """A light whose effects map to the pool LED's 11 colors + 7 sequences."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF
    _attr_effect_list = MODES

    def __init__(self, controller: PoolRGBController, entry: ConfigEntry) -> None:
        self._controller = controller
        self._entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or "Pool RGB LED",
            manufacturer="Generic",
            model="Power-cycle RGB LED",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._controller.add_listener(self.async_write_ha_state))

    @property
    def is_on(self) -> bool:
        return self._controller.is_on

    @property
    def effect(self) -> str | None:
        return self._controller.mode

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        mode = self._controller.mode
        return {
            ATTR_MODE: mode,
            ATTR_INDEX: self._controller.index,
            ATTR_KIND: "color" if mode in COLORS else "sequence",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        effect = kwargs.get(ATTR_EFFECT)
        if not self._controller.is_on:
            await self._controller.async_turn_on()
        if effect is not None and effect != self._controller.mode:
            await self._controller.async_set_mode(effect)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._controller.async_turn_off()

    async def async_service_resync(self) -> None:
        await self._controller.async_resync()

    async def async_service_next(self) -> None:
        await self._controller.async_next()

    async def async_service_set_mode(self, mode: str) -> None:
        await self._controller.async_set_mode(mode)
