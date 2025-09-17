from __future__ import annotations
import re
import voluptuous as vol
import datetime as dt
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.helpers.typing import ConfigType
from homeassistant.components import webhook as webhook_comp
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN, CONF_SIP_HOST, CONF_SIP_PORT, CONF_WEBHOOK_ID
)
# We will call hassio.addon_stdin directly
ADDON_SLUG = "c7744bff_ha-sip"
SIGNAL_CALL_STATE = "hacs_unifi_talk_call_state"


def _mk_sip_uri(number: str, host: str) -> str:
    n = (number or "").strip()
    if n.startswith("sip:"):
        return n
    # if it's digits / **feature codes, turn into sip:<n>@host
    if re.fullmatch(r"[\d*#]+", n):
        return f"sip:{n}@{host}"
    # else pass through
    return n

DIAL_SCHEMA = vol.Schema({
    vol.Required("number"): str,
    vol.Optional("ring_timeout", default=300): int,
    vol.Optional("sip_account", default=1): int,
    vol.Optional("menu", default={}): dict,
    vol.Optional("webhook_to_call", default={}): dict,
})

HANGUP_SCHEMA = vol.Schema({vol.Required("number"): str})

DTMF_SCHEMA = vol.Schema({
    vol.Required("number"): str,
    vol.Required("digits"): str,
    vol.Optional("method", default="in_band"): vol.In(["in_band","rfc2833","sip_info"]),
})

TRANSFER_SCHEMA = vol.Schema({
    vol.Required("number"): str,
    vol.Required("transfer_to"): str,
})

BRIDGE_SCHEMA = vol.Schema({
    vol.Required("number"): str,
    vol.Required("bridge_to"): str,
})

PLAY_MESSAGE_SCHEMA = vol.Schema({
    vol.Required("number"): str,
    vol.Required("message"): str,
    vol.Optional("tts_language"): str,
    vol.Optional("cache_audio", default=False): bool,
    vol.Optional("wait_for_audio_to_finish", default=False): bool,
})

PLAY_AUDIO_FILE_SCHEMA = vol.Schema({
    vol.Required("number"): str,
    vol.Required("audio_file"): str,
    vol.Optional("cache_audio", default=False): bool,
    vol.Optional("wait_for_audio_to_finish", default=False): bool,
})

STOP_PLAYBACK_SCHEMA = vol.Schema({vol.Required("number"): str})

ANSWER_SCHEMA = vol.Schema({
    vol.Required("number"): str,
    vol.Optional("menu", default={}): dict,
    vol.Optional("webhook_to_call", default={}): dict,
})

async def _stdin(hass: HomeAssistant, payload: dict) -> None:
    await hass.services.async_call(
        "hassio", "addon_stdin",
        {"addon": ADDON_SLUG, "input": payload},
        blocking=True,
    )

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data
    host = entry.data.get(CONF_SIP_HOST, "192.168.1.1")
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "config": entry.data,
        "state": {
            "event": "idle",
            "caller": None,
            "parsed_caller": None,
            "sip_account": None,
            "internal_id": None,
            "last_dtmf_digit": None,
            "last_type": None,
            "last_message": None,
            "last_audio_file": None,
            "updated": None,
        }
    }

    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    if webhook_id:
        async def _handle_webhook(hass: HomeAssistant, webhook_id: str, request):
            payload = await request.json()
            now = dt.datetime.now(dt.timezone.utc).isoformat()

            s = hass.data[DOMAIN][entry.entry_id]["state"]
            s["event"] = payload.get("event")
            s["caller"] = payload.get("caller")
            s["parsed_caller"] = payload.get("parsed_caller")
            s["sip_account"] = payload.get("sip_account")
            s["internal_id"] = payload.get("internal_id")
            if payload.get("event") == "dtmf_digit":
                s["last_dtmf_digit"] = payload.get("digit")
            if payload.get("event") == "playback_done":
                s["last_type"] = payload.get("type")
                s["last_message"] = payload.get("message")
                s["last_audio_file"] = payload.get("audio_file")
            s["updated"] = now

            # Update entities
            async_dispatcher_send(hass, f"{SIGNAL_CALL_STATE}_{entry.entry_id}")

            # Re-emit as HA event for Node-RED
            hass.bus.async_fire("hacs_unifi_talk_webhook", payload)

            return None

        # safe re-register
        try:
            webhook_comp.async_unregister(hass, webhook_id)
        except Exception:
            pass
        webhook_comp.async_register(hass, DOMAIN, "ha-sip", webhook_id, _handle_webhook)

    async def dial(call: ServiceCall) -> None:
        data = DIAL_SCHEMA(call.data)
        number = _mk_sip_uri(data["number"], host)
        payload = {
            "command": "dial",
            "number": number,
            "ring_timeout": data["ring_timeout"],
            "sip_account": data["sip_account"],
            "webhook_to_call": data["webhook_to_call"],
            "menu": data["menu"],
        }
        await _stdin(hass, payload)

    async def hangup(call: ServiceCall) -> None:
        data = HANGUP_SCHEMA(call.data)
        await _stdin(hass, {"command": "hangup", "number": _mk_sip_uri(data["number"], host)})

    async def send_dtmf(call: ServiceCall) -> None:
        data = DTMF_SCHEMA(call.data)
        await _stdin(hass, {
            "command": "send_dtmf",
            "number": _mk_sip_uri(data["number"], host),
            "digits": data["digits"],
            "method": data["method"],
        })

    async def transfer(call: ServiceCall) -> None:
        data = TRANSFER_SCHEMA(call.data)
        await _stdin(hass, {
            "command": "transfer",
            "number": _mk_sip_uri(data["number"], host),
            "transfer_to": _mk_sip_uri(data["transfer_to"], host),
        })

    async def bridge(call: ServiceCall) -> None:
        data = BRIDGE_SCHEMA(call.data)
        await _stdin(hass, {
            "command": "bridge_audio",
            "number": _mk_sip_uri(data["number"], host),
            "bridge_to": _mk_sip_uri(data["bridge_to"], host),
        })

    async def play_message(call: ServiceCall) -> None:
        data = PLAY_MESSAGE_SCHEMA(call.data)
        p = {
            "command": "play_message",
            "number": _mk_sip_uri(data["number"], host),
            "message": data["message"],
            "cache_audio": data["cache_audio"],
            "wait_for_audio_to_finish": data["wait_for_audio_to_finish"],
        }
        if data.get("tts_language"):
            p["tts_language"] = data["tts_language"]
        await _stdin(hass, p)

    async def play_audio_file(call: ServiceCall) -> None:
        data = PLAY_AUDIO_FILE_SCHEMA(call.data)
        await _stdin(hass, {
            "command": "play_audio_file",
            "number": _mk_sip_uri(data["number"], host),
            "audio_file": data["audio_file"],
            "cache_audio": data["cache_audio"],
            "wait_for_audio_to_finish": data["wait_for_audio_to_finish"],
        })

    async def stop_playback(call: ServiceCall) -> None:
        data = STOP_PLAYBACK_SCHEMA(call.data)
        await _stdin(hass, {"command": "stop_playback", "number": _mk_sip_uri(data["number"], host)})

    async def answer(call: ServiceCall) -> None:
        data = ANSWER_SCHEMA(call.data)
        await _stdin(hass, {
            "command": "answer",
            "number": data["number"],  # internal id; don't rewrite
            "webhook_to_call": data["webhook_to_call"],
            "menu": data["menu"],
        })

    hass.services.async_register(DOMAIN, "dial", dial)
    hass.services.async_register(DOMAIN, "hangup", hangup)
    hass.services.async_register(DOMAIN, "send_dtmf", send_dtmf)
    hass.services.async_register(DOMAIN, "transfer", transfer)
    hass.services.async_register(DOMAIN, "bridge_audio", bridge)
    hass.services.async_register(DOMAIN, "play_message", play_message)
    hass.services.async_register(DOMAIN, "play_audio_file", play_audio_file)
    hass.services.async_register(DOMAIN, "stop_playback", stop_playback)
    hass.services.async_register(DOMAIN, "answer", answer)

    # Forward to sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # services are not namespaced per entry, so we leave them; in a future version use helpers.service.async_register_admin_service with unique names
    hass.data[DOMAIN].pop(entry.entry_id, None)
    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    if webhook_id:
        try:
            webhook_comp.async_unregister(hass, webhook_id)
        except Exception:
            pass
    await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
