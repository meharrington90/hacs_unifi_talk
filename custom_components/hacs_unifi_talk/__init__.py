from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import re
from typing import Any

from aiohttp import web
import voluptuous as vol

from homeassistant.components import webhook as webhook_comp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from .const import (
    ADDON_SLUG,
    CONF_SIP_HOST,
    CONF_WEBHOOK_ID,
    DATA_ENTRIES,
    DATA_SERVICES_REGISTERED,
    DOMAIN,
    EVENT_WEBHOOK,
    PLATFORMS,
    SIGNAL_CALL_STATE,
)
from .supervisor import SupervisorError, set_system_managed

_LOGGER = logging.getLogger(__name__)

SERVICE_DIAL = "dial"
SERVICE_HANGUP = "hangup"
SERVICE_SEND_DTMF = "send_dtmf"
SERVICE_TRANSFER = "transfer"
SERVICE_BRIDGE_AUDIO = "bridge_audio"
SERVICE_PLAY_MESSAGE = "play_message"
SERVICE_PLAY_AUDIO_FILE = "play_audio_file"
SERVICE_STOP_PLAYBACK = "stop_playback"
SERVICE_ANSWER = "answer"

NON_EMPTY_STRING = vol.All(cv.string, vol.Length(min=1))

DIAL_SCHEMA = vol.Schema(
    {
        vol.Required("number"): NON_EMPTY_STRING,
        vol.Optional("ring_timeout", default=300): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
        vol.Optional("sip_account", default=1): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
        vol.Optional("menu"): dict,
        vol.Optional("webhook_to_call"): dict,
    },
    extra=vol.PREVENT_EXTRA,
)

HANGUP_SCHEMA = vol.Schema(
    {vol.Required("number"): NON_EMPTY_STRING},
    extra=vol.PREVENT_EXTRA,
)

DTMF_SCHEMA = vol.Schema(
    {
        vol.Required("number"): NON_EMPTY_STRING,
        vol.Required("digits"): NON_EMPTY_STRING,
        vol.Optional("method", default="in_band"): vol.In(
            ("in_band", "rfc2833", "sip_info")
        ),
    },
    extra=vol.PREVENT_EXTRA,
)

TRANSFER_SCHEMA = vol.Schema(
    {
        vol.Required("number"): NON_EMPTY_STRING,
        vol.Required("transfer_to"): NON_EMPTY_STRING,
    },
    extra=vol.PREVENT_EXTRA,
)

BRIDGE_SCHEMA = vol.Schema(
    {
        vol.Required("number"): NON_EMPTY_STRING,
        vol.Required("bridge_to"): NON_EMPTY_STRING,
    },
    extra=vol.PREVENT_EXTRA,
)

PLAY_MESSAGE_SCHEMA = vol.Schema(
    {
        vol.Required("number"): NON_EMPTY_STRING,
        vol.Required("message"): NON_EMPTY_STRING,
        vol.Optional("tts_language"): cv.string,
        vol.Optional("cache_audio", default=False): bool,
        vol.Optional("wait_for_audio_to_finish", default=False): bool,
    },
    extra=vol.PREVENT_EXTRA,
)

PLAY_AUDIO_FILE_SCHEMA = vol.Schema(
    {
        vol.Required("number"): NON_EMPTY_STRING,
        vol.Required("audio_file"): NON_EMPTY_STRING,
        vol.Optional("cache_audio", default=False): bool,
        vol.Optional("wait_for_audio_to_finish", default=False): bool,
    },
    extra=vol.PREVENT_EXTRA,
)

STOP_PLAYBACK_SCHEMA = vol.Schema(
    {vol.Required("number"): NON_EMPTY_STRING},
    extra=vol.PREVENT_EXTRA,
)

ANSWER_SCHEMA = vol.Schema(
    {
        vol.Required("number"): NON_EMPTY_STRING,
        vol.Optional("menu"): dict,
        vol.Optional("webhook_to_call"): dict,
    },
    extra=vol.PREVENT_EXTRA,
)


@dataclass
class UniFiTalkRuntimeData:
    config: dict[str, Any]
    state: dict[str, Any] = field(default_factory=dict)


def _default_state() -> dict[str, Any]:
    return {
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


def _normalize_sip_target(number: str, host: str) -> str:
    target = number.strip()
    if target.startswith(("sip:", "sips:", "tel:")):
        return target
    if "@" in target:
        return f"sip:{target}"
    if re.fullmatch(r"[A-Za-z0-9+*#._-]+", target):
        return f"sip:{target}@{host}"
    return target


def _get_runtime(hass: HomeAssistant) -> UniFiTalkRuntimeData:
    entries: dict[str, UniFiTalkRuntimeData] = hass.data[DOMAIN][DATA_ENTRIES]
    if not entries:
        raise HomeAssistantError(
            "UniFi Talk is not configured. Add the integration first."
        )
    return next(iter(entries.values()))


async def _stdin(hass: HomeAssistant, payload: dict[str, Any]) -> None:
    if not hass.services.has_service("hassio", "addon_stdin"):
        raise HomeAssistantError(
            "The Home Assistant Supervisor add-on API is not available."
        )

    await hass.services.async_call(
        "hassio",
        "addon_stdin",
        {"addon": ADDON_SLUG, "input": payload},
        blocking=True,
    )


def _register_services(hass: HomeAssistant) -> None:
    if hass.data[DOMAIN][DATA_SERVICES_REGISTERED]:
        return

    async def dial(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        host = runtime.config[CONF_SIP_HOST]
        await _stdin(
            hass,
            {
                "command": SERVICE_DIAL,
                "number": _normalize_sip_target(call.data["number"], host),
                "ring_timeout": call.data["ring_timeout"],
                "sip_account": call.data["sip_account"],
                "menu": call.data.get("menu", {}),
                "webhook_to_call": call.data.get("webhook_to_call", {}),
            },
        )

    async def hangup(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        host = runtime.config[CONF_SIP_HOST]
        await _stdin(
            hass,
            {
                "command": SERVICE_HANGUP,
                "number": _normalize_sip_target(call.data["number"], host),
            },
        )

    async def send_dtmf(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        host = runtime.config[CONF_SIP_HOST]
        await _stdin(
            hass,
            {
                "command": SERVICE_SEND_DTMF,
                "number": _normalize_sip_target(call.data["number"], host),
                "digits": call.data["digits"],
                "method": call.data["method"],
            },
        )

    async def transfer(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        host = runtime.config[CONF_SIP_HOST]
        await _stdin(
            hass,
            {
                "command": SERVICE_TRANSFER,
                "number": _normalize_sip_target(call.data["number"], host),
                "transfer_to": _normalize_sip_target(call.data["transfer_to"], host),
            },
        )

    async def bridge_audio(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        host = runtime.config[CONF_SIP_HOST]
        await _stdin(
            hass,
            {
                "command": SERVICE_BRIDGE_AUDIO,
                "number": _normalize_sip_target(call.data["number"], host),
                "bridge_to": _normalize_sip_target(call.data["bridge_to"], host),
            },
        )

    async def play_message(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        host = runtime.config[CONF_SIP_HOST]
        payload = {
            "command": SERVICE_PLAY_MESSAGE,
            "number": _normalize_sip_target(call.data["number"], host),
            "message": call.data["message"],
            "cache_audio": call.data["cache_audio"],
            "wait_for_audio_to_finish": call.data["wait_for_audio_to_finish"],
        }
        if call.data.get("tts_language"):
            payload["tts_language"] = call.data["tts_language"]
        await _stdin(hass, payload)

    async def play_audio_file(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        host = runtime.config[CONF_SIP_HOST]
        await _stdin(
            hass,
            {
                "command": SERVICE_PLAY_AUDIO_FILE,
                "number": _normalize_sip_target(call.data["number"], host),
                "audio_file": call.data["audio_file"],
                "cache_audio": call.data["cache_audio"],
                "wait_for_audio_to_finish": call.data["wait_for_audio_to_finish"],
            },
        )

    async def stop_playback(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        host = runtime.config[CONF_SIP_HOST]
        await _stdin(
            hass,
            {
                "command": SERVICE_STOP_PLAYBACK,
                "number": _normalize_sip_target(call.data["number"], host),
            },
        )

    async def answer(call: ServiceCall) -> None:
        await _stdin(
            hass,
            {
                "command": SERVICE_ANSWER,
                "number": call.data["number"],
                "menu": call.data.get("menu", {}),
                "webhook_to_call": call.data.get("webhook_to_call", {}),
            },
        )

    hass.services.async_register(DOMAIN, SERVICE_DIAL, dial, schema=DIAL_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_HANGUP, hangup, schema=HANGUP_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_SEND_DTMF, send_dtmf, schema=DTMF_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_TRANSFER, transfer, schema=TRANSFER_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_BRIDGE_AUDIO, bridge_audio, schema=BRIDGE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_PLAY_MESSAGE, play_message, schema=PLAY_MESSAGE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_AUDIO_FILE,
        play_audio_file,
        schema=PLAY_AUDIO_FILE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_PLAYBACK, stop_playback, schema=STOP_PLAYBACK_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_ANSWER, answer, schema=ANSWER_SCHEMA)
    hass.data[DOMAIN][DATA_SERVICES_REGISTERED] = True


def _merge_entry_config(entry: ConfigEntry) -> dict[str, Any]:
    return {**entry.data, **entry.options}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(
        DOMAIN,
        {
            DATA_ENTRIES: {},
            DATA_SERVICES_REGISTERED: False,
        },
    )
    _register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(
        DOMAIN,
        {
            DATA_ENTRIES: {},
            DATA_SERVICES_REGISTERED: False,
        },
    )
    _register_services(hass)

    config = _merge_entry_config(entry)
    runtime = UniFiTalkRuntimeData(config=config, state=_default_state())
    hass.data[DOMAIN][DATA_ENTRIES][entry.entry_id] = runtime

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    webhook_id = config.get(CONF_WEBHOOK_ID)
    if webhook_id:

        async def _handle_webhook(
            hass: HomeAssistant, webhook_id: str, request: web.Request
        ) -> web.Response:
            del webhook_id
            try:
                payload = await request.json()
            except ValueError:
                return web.Response(status=400, text="Expected JSON payload")

            state = runtime.state
            state["event"] = payload.get("event") or "idle"
            state["caller"] = payload.get("caller")
            state["parsed_caller"] = payload.get("parsed_caller")
            state["sip_account"] = payload.get("sip_account")
            state["internal_id"] = payload.get("internal_id")
            if payload.get("event") == "dtmf_digit":
                state["last_dtmf_digit"] = payload.get("digit")
            if payload.get("event") == "playback_done":
                state["last_type"] = payload.get("type")
                state["last_message"] = payload.get("message")
                state["last_audio_file"] = payload.get("audio_file")
            state["updated"] = datetime.now(timezone.utc).isoformat()

            async_dispatcher_send(hass, f"{SIGNAL_CALL_STATE}_{entry.entry_id}")
            hass.bus.async_fire(EVENT_WEBHOOK, payload)

            return web.Response(status=200)

        try:
            webhook_comp.async_unregister(hass, webhook_id)
        except ValueError:
            pass

        webhook_comp.async_register(
            hass, DOMAIN, "UniFi Talk", webhook_id, _handle_webhook
        )

    try:
        await set_system_managed(hass, entry.entry_id)
    except SupervisorError as err:
        _LOGGER.debug("Unable to mark ha-sip add-on as system managed: %s", err)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    runtime = hass.data[DOMAIN][DATA_ENTRIES].pop(entry.entry_id, None)
    if runtime:
        webhook_id = runtime.config.get(CONF_WEBHOOK_ID)
        if webhook_id:
            try:
                webhook_comp.async_unregister(hass, webhook_id)
            except ValueError:
                pass

    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
