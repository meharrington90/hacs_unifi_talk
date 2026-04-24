from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import UniFiTalkConfigEntry
from .const import CONF_PASSWORD, CONF_SIP_HOST, CONF_SSH_PASSWORD, CONF_WEBHOOK_ID

TO_REDACT = {
    CONF_PASSWORD,
    CONF_SSH_PASSWORD,
    CONF_SIP_HOST,
    CONF_WEBHOOK_ID,
    "caller",
    "parsed_caller",
    "default_target",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: UniFiTalkConfigEntry
) -> dict[str, Any]:
    del hass
    runtime = entry.runtime_data
    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "entry_options": async_redact_data(dict(entry.options), TO_REDACT),
        "runtime_summary": async_redact_data(runtime.summary(), TO_REDACT),
        "recent_events": async_redact_data(runtime.recent_events, TO_REDACT),
        "calls": async_redact_data(
            {
                internal_id: session.to_dict()
                for internal_id, session in runtime.calls.items()
            },
            TO_REDACT,
        ),
    }
