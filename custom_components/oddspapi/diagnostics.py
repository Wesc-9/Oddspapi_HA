"""Diagnostics support for OddsPapi Sports Odds."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics with the API key removed."""
    coordinator = entry.runtime_data
    return async_redact_data(
        {
            "config": dict(entry.data),
            "options": dict(entry.options),
            "data": coordinator.data,
        },
        {CONF_API_KEY},
    )
