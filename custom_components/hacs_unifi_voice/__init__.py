from __future__ import annotations
import re
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import CONF_HOST, CONF_PORT
from .const import DOMAIN, CONF_ADDON

SERVICE_CALL = "call"

SERVICE_SCHEMA = vol.Schema({
    vol.Required("phone_number"): str,
    vol.Required("message_tts"): str,
    vol.Optional(CONF_HOST, default="192.168.1.1"): str,
    vol.Optional(CONF_PORT, default=5060): int,
    vol.Optional(CONF_ADDON, default="89275b70_dss_voip"): str,
})

def _normalize_number(num: str) -> str:
    num = re.sub(r"[^\d+]", "", num or "")
    return "+" + re.sub(r"^\+?", "", num)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    async def handle_call(call: ServiceCall) -> None:
        host = call.data.get(CONF_HOST)
        port = call.data.get(CONF_PORT)
        addon = call.data.get(CONF_ADDON)
        number = _normalize_number(call.data["phone_number"])
        msg = call.data["message_tts"]
        sip_uri = f"sip:{number}@{host}:{port}"

        await hass.services.async_call(
            "hassio",
            "addon_stdin",
            {"addon": addon, "input": {"call_sip_uri": sip_uri, "message_tts": msg}},
            blocking=True,
        )

    hass.services.async_register(DOMAIN, SERVICE_CALL, handle_call, schema=SERVICE_SCHEMA)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {}
    return True

async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    if hass.services.has_service(DOMAIN, SERVICE_CALL):
        hass.services.async_remove(DOMAIN, SERVICE_CALL)
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
