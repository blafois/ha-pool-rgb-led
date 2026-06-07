"""Config flow for Pool RGB LED."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

import re

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
)

_KNX_GA_RE = re.compile(r"^\d+(/\d+){1,2}$")


def _validate_knx_address(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not _KNX_GA_RE.match(value):
        raise vol.Invalid("invalid_knx_address")
    return value


def _entity_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["light", "switch", "input_boolean"])
    )


def _ms_selector(default: int) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=50,
            max=5000,
            step=50,
            unit_of_measurement="ms",
            mode=selector.NumberSelectorMode.BOX,
        )
    )


class PoolRGBLEDConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}

        if user_input is not None:
            target = user_input.get(CONF_TARGET_ENTITY) or None
            try:
                knx_addr = _validate_knx_address(user_input.get(CONF_KNX_ADDRESS))
            except vol.Invalid:
                errors[CONF_KNX_ADDRESS] = "invalid_knx_address"
                knx_addr = None

            if not errors and not target and not knx_addr:
                errors["base"] = "need_target_or_knx"

            if not errors:
                unique_key = knx_addr or target
                await self.async_set_unique_id(f"{DOMAIN}:{unique_key}")
                self._abort_if_unique_id_configured()
                title = f"Pool RGB LED ({knx_addr or target})"
                data: dict[str, Any] = {}
                if target:
                    data[CONF_TARGET_ENTITY] = target
                if knx_addr:
                    data[CONF_KNX_ADDRESS] = knx_addr
                return self.async_create_entry(
                    title=title,
                    data=data,
                    options={
                        CONF_PULSE_MS: user_input.get(CONF_PULSE_MS, DEFAULT_PULSE_MS),
                        CONF_GAP_MS: user_input.get(CONF_GAP_MS, DEFAULT_GAP_MS),
                        CONF_SETTLE_MS: user_input.get(
                            CONF_SETTLE_MS, DEFAULT_SETTLE_MS
                        ),
                    },
                )

        schema = vol.Schema(
            {
                vol.Optional(CONF_TARGET_ENTITY): _entity_selector(),
                vol.Optional(CONF_KNX_ADDRESS): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(CONF_PULSE_MS, default=DEFAULT_PULSE_MS): _ms_selector(
                    DEFAULT_PULSE_MS
                ),
                vol.Optional(CONF_GAP_MS, default=DEFAULT_GAP_MS): _ms_selector(
                    DEFAULT_GAP_MS
                ),
                vol.Optional(CONF_SETTLE_MS, default=DEFAULT_SETTLE_MS): _ms_selector(
                    DEFAULT_SETTLE_MS
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return PoolRGBLEDOptionsFlow(entry)


class PoolRGBLEDOptionsFlow(OptionsFlow):
    """Edit timings and the target entity after install."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}

        if user_input is not None:
            target = user_input.get(CONF_TARGET_ENTITY) or None
            try:
                knx_addr = _validate_knx_address(user_input.get(CONF_KNX_ADDRESS))
            except vol.Invalid:
                errors[CONF_KNX_ADDRESS] = "invalid_knx_address"
                knx_addr = None

            if not errors and not target and not knx_addr:
                errors["base"] = "need_target_or_knx"

            if not errors:
                cleaned: dict[str, Any] = {
                    CONF_PULSE_MS: user_input.get(CONF_PULSE_MS, DEFAULT_PULSE_MS),
                    CONF_GAP_MS: user_input.get(CONF_GAP_MS, DEFAULT_GAP_MS),
                    CONF_SETTLE_MS: user_input.get(CONF_SETTLE_MS, DEFAULT_SETTLE_MS),
                }
                if target:
                    cleaned[CONF_TARGET_ENTITY] = target
                if knx_addr:
                    cleaned[CONF_KNX_ADDRESS] = knx_addr
                return self.async_create_entry(title="", data=cleaned)

        opts = self._entry.options
        data = self._entry.data
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_TARGET_ENTITY,
                    description={
                        "suggested_value": opts.get(
                            CONF_TARGET_ENTITY, data.get(CONF_TARGET_ENTITY)
                        )
                    },
                ): _entity_selector(),
                vol.Optional(
                    CONF_KNX_ADDRESS,
                    description={
                        "suggested_value": opts.get(
                            CONF_KNX_ADDRESS, data.get(CONF_KNX_ADDRESS)
                        )
                    },
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(
                    CONF_PULSE_MS,
                    default=opts.get(CONF_PULSE_MS, DEFAULT_PULSE_MS),
                ): _ms_selector(DEFAULT_PULSE_MS),
                vol.Optional(
                    CONF_GAP_MS,
                    default=opts.get(CONF_GAP_MS, DEFAULT_GAP_MS),
                ): _ms_selector(DEFAULT_GAP_MS),
                vol.Optional(
                    CONF_SETTLE_MS,
                    default=opts.get(CONF_SETTLE_MS, DEFAULT_SETTLE_MS),
                ): _ms_selector(DEFAULT_SETTLE_MS),
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
