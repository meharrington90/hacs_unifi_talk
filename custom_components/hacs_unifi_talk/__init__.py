from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
import re
from typing import Any

from aiohttp import web
import voluptuous as vol

from homeassistant.components import webhook as webhook_comp
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from .const import (
    ADDON_SLUG,
    CALL_EVENT_TYPES,
    CONF_DEFAULT_TARGET,
    CONF_NOTIFY_HANGUP,
    CONF_NOTIFY_RING_TIMEOUT,
    CONF_NOTIFY_SIP_ACCOUNT,
    CONF_SIP_HOST,
    CONF_WEBHOOK_ID,
    DATA_SERVICES_REGISTERED,
    DEFAULT_NOTIFY_RING_TIMEOUT,
    DEFAULT_NOTIFY_SIP_ACCOUNT,
    DOMAIN,
    EVENT_WEBHOOK,
    NOTIFY_OPTION_KEYS,
    PLATFORMS,
    SIGNAL_CALL_STATE,
    TERMINAL_CALL_EVENTS,
)
from .supervisor import SupervisorError, get_addon_info, set_system_managed

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
SERVICE_ANNOUNCE = "announce"
SERVICE_ANSWER_AND_SPEAK = "answer_and_speak"

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

ANNOUNCE_SCHEMA = vol.Schema(
    {
        vol.Required("number"): NON_EMPTY_STRING,
        vol.Required("message"): NON_EMPTY_STRING,
        vol.Optional("title"): cv.string,
        vol.Optional("tts_language"): cv.string,
        vol.Optional("ring_timeout", default=DEFAULT_NOTIFY_RING_TIMEOUT): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
        vol.Optional("sip_account", default=DEFAULT_NOTIFY_SIP_ACCOUNT): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
        vol.Optional("hangup_after_speaking", default=True): bool,
        vol.Optional("webhook_to_call"): dict,
    },
    extra=vol.PREVENT_EXTRA,
)

ANSWER_AND_SPEAK_SCHEMA = vol.Schema(
    {
        vol.Required("number"): NON_EMPTY_STRING,
        vol.Required("message"): NON_EMPTY_STRING,
        vol.Optional("title"): cv.string,
        vol.Optional("tts_language"): cv.string,
        vol.Optional("hangup_after_speaking", default=True): bool,
        vol.Optional("webhook_to_call"): dict,
    },
    extra=vol.PREVENT_EXTRA,
)


@dataclass
class CallSession:
    internal_id: str
    direction: str = "unknown"
    state: str = "idle"
    last_event: str = "idle"
    caller: str | None = None
    parsed_caller: str | None = None
    sip_account: int | None = None
    menu_id: str | None = None
    last_dtmf_digit: str | None = None
    last_type: str | None = None
    last_message: str | None = None
    last_audio_file: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    established_at: str | None = None
    disconnected_at: str | None = None
    event_count: int = 0

    @property
    def active(self) -> bool:
        return self.last_event not in TERMINAL_CALL_EVENTS

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["active"] = self.active
        return payload


@dataclass
class UniFiTalkRuntimeData:
    config: dict[str, Any]
    calls: dict[str, CallSession] = field(default_factory=dict)
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    last_payload: dict[str, Any] = field(default_factory=dict)
    last_event: str = "idle"
    last_updated: str | None = None
    last_caller: str | None = None
    last_internal_id: str | None = None
    last_incoming_call: dict[str, Any] | None = None
    last_dtmf_digit: str | None = None
    last_menu_id: str | None = None
    last_message: str | None = None
    last_audio_file: str | None = None

    def active_calls(self) -> list[CallSession]:
        return [session for session in self.calls.values() if session.active]

    def recent_call_snapshots(self, limit: int = 10) -> list[dict[str, Any]]:
        sessions = sorted(
            self.calls.values(),
            key=lambda session: session.updated_at or "",
            reverse=True,
        )
        return [session.to_dict() for session in sessions[:limit]]

    def summary(self) -> dict[str, Any]:
        active = self.active_calls()
        return {
            "last_event": self.last_event,
            "last_updated": self.last_updated,
            "last_caller": self.last_caller,
            "last_internal_id": self.last_internal_id,
            "last_dtmf_digit": self.last_dtmf_digit,
            "last_menu_id": self.last_menu_id,
            "last_message": self.last_message,
            "last_audio_file": self.last_audio_file,
            "active_call_count": len(active),
            "active_call_ids": [session.internal_id for session in active],
            "active_calls": [session.to_dict() for session in active[:5]],
            "recent_calls": self.recent_call_snapshots(5),
        }


type UniFiTalkConfigEntry = ConfigEntry[UniFiTalkRuntimeData]


def _merge_entry_config(entry: ConfigEntry) -> dict[str, Any]:
    merged = dict(entry.data)
    for key in NOTIFY_OPTION_KEYS:
        if key in entry.options:
            merged[key] = entry.options[key]
    return merged


def _normalize_sip_target(number: str, host: str) -> str:
    target = number.strip()
    if target.startswith(("sip:", "sips:", "tel:")):
        return target
    if "@" in target:
        return f"sip:{target}"
    if re.fullmatch(r"[A-Za-z0-9+*#._-]+", target):
        return f"sip:{target}@{host}"
    return target


def _state_for_event(event: str, current: str) -> str:
    return {
        "incoming_call": "ringing",
        "call_established": "active",
        "entered_menu": "menu",
        "dtmf_digit": current if current != "idle" else "active",
        "playback_done": current if current != "idle" else "active",
        "ring_timeout": "timed_out",
        "timeout": "timed_out",
        "call_disconnected": "disconnected",
    }.get(event, current)


def _compose_message(message: str, title: str | None) -> str:
    clean_message = message.strip()
    clean_title = (title or "").strip()
    if not clean_title:
        return clean_message
    return f"{clean_title}. {clean_message}"


def _build_menu_message(
    message: str,
    title: str | None = None,
    tts_language: str | None = None,
    hangup_after_speaking: bool = False,
) -> dict[str, Any]:
    menu: dict[str, Any] = {
        "message": _compose_message(message, title),
        "post_action": "hangup" if hangup_after_speaking else "noop",
    }
    if tts_language:
        menu["language"] = tts_language
    return menu


def _get_runtime(hass: HomeAssistant) -> UniFiTalkRuntimeData:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED and entry.runtime_data is not None:
            return entry.runtime_data

    raise ServiceValidationError(
        "UniFi Talk is not configured or not currently loaded.",
    )


async def _stdin(hass: HomeAssistant, payload: dict[str, Any]) -> None:
    if not hass.services.has_service("hassio", "addon_stdin"):
        raise ServiceValidationError(
            "The Home Assistant Supervisor add-on API is not available.",
        )

    await hass.services.async_call(
        "hassio",
        "addon_stdin",
        {"addon": ADDON_SLUG, "input": payload},
        blocking=True,
    )


def _append_recent_event(
    runtime: UniFiTalkRuntimeData, event_data: dict[str, Any], now: str
) -> None:
    runtime.recent_events.insert(
        0,
        {
            "timestamp": now,
            "event": event_data.get("event"),
            "internal_id": event_data.get("internal_id"),
            "parsed_caller": event_data.get("parsed_caller"),
            "menu_id": event_data.get("menu_id"),
            "digit": event_data.get("digit"),
        },
    )
    del runtime.recent_events[25:]


def _prune_call_sessions(runtime: UniFiTalkRuntimeData) -> None:
    if len(runtime.calls) <= 25:
        return

    active_ids = {session.internal_id for session in runtime.active_calls()}
    inactive_sessions = sorted(
        (session for session in runtime.calls.values() if not session.active),
        key=lambda session: session.updated_at or "",
        reverse=True,
    )
    keep_ids = active_ids | {session.internal_id for session in inactive_sessions[:15]}
    runtime.calls = {
        internal_id: session
        for internal_id, session in runtime.calls.items()
        if internal_id in keep_ids
    }


def _update_runtime_from_webhook(
    runtime: UniFiTalkRuntimeData, payload: dict[str, Any]
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    event = payload.get("event") or "idle"
    internal_id = payload.get("internal_id")
    parsed_caller = payload.get("parsed_caller")
    caller = payload.get("caller")

    runtime.last_payload = dict(payload)
    runtime.last_event = event
    runtime.last_updated = now
    runtime.last_caller = parsed_caller or caller or runtime.last_caller
    runtime.last_internal_id = internal_id or runtime.last_internal_id

    if event == "incoming_call":
        runtime.last_incoming_call = {
            "timestamp": now,
            "caller": caller,
            "parsed_caller": parsed_caller,
            "sip_account": payload.get("sip_account"),
            "internal_id": internal_id,
        }
    if event == "dtmf_digit":
        runtime.last_dtmf_digit = payload.get("digit")
    if event == "entered_menu":
        runtime.last_menu_id = payload.get("menu_id")
    if event == "playback_done":
        runtime.last_message = payload.get("message")
        runtime.last_audio_file = payload.get("audio_file")

    _append_recent_event(runtime, payload, now)

    if internal_id:
        session = runtime.calls.get(internal_id)
        if session is None:
            session = CallSession(
                internal_id=internal_id,
                direction="incoming" if event == "incoming_call" else "outgoing",
                created_at=now,
            )
            runtime.calls[internal_id] = session

        if event == "incoming_call":
            session.direction = "incoming"
        elif session.direction == "unknown":
            session.direction = "outgoing"

        session.state = _state_for_event(event, session.state)
        session.last_event = event
        session.caller = caller or session.caller
        session.parsed_caller = parsed_caller or session.parsed_caller
        session.sip_account = payload.get("sip_account", session.sip_account)
        session.updated_at = now
        session.event_count += 1

        if payload.get("menu_id"):
            session.menu_id = payload["menu_id"]
        if payload.get("digit"):
            session.last_dtmf_digit = payload["digit"]
        if payload.get("type"):
            session.last_type = payload["type"]
        if payload.get("message"):
            session.last_message = payload["message"]
        if payload.get("audio_file"):
            session.last_audio_file = payload["audio_file"]
        if event == "call_established" and session.established_at is None:
            session.established_at = now
        if event in TERMINAL_CALL_EVENTS:
            session.disconnected_at = now

    _prune_call_sessions(runtime)
    return {
        "event": event,
        "internal_id": internal_id,
        "caller": caller,
        "parsed_caller": parsed_caller,
        "digit": payload.get("digit"),
        "menu_id": payload.get("menu_id"),
        "sip_account": payload.get("sip_account"),
        "timestamp": now,
    }


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

    async def announce(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        host = runtime.config[CONF_SIP_HOST]
        await _stdin(
            hass,
            {
                "command": SERVICE_DIAL,
                "number": _normalize_sip_target(call.data["number"], host),
                "ring_timeout": call.data["ring_timeout"],
                "sip_account": call.data["sip_account"],
                "webhook_to_call": call.data.get("webhook_to_call", {}),
                "menu": _build_menu_message(
                    message=call.data["message"],
                    title=call.data.get("title"),
                    tts_language=call.data.get("tts_language"),
                    hangup_after_speaking=call.data["hangup_after_speaking"],
                ),
            },
        )

    async def answer_and_speak(call: ServiceCall) -> None:
        await _stdin(
            hass,
            {
                "command": SERVICE_ANSWER,
                "number": call.data["number"],
                "webhook_to_call": call.data.get("webhook_to_call", {}),
                "menu": _build_menu_message(
                    message=call.data["message"],
                    title=call.data.get("title"),
                    tts_language=call.data.get("tts_language"),
                    hangup_after_speaking=call.data["hangup_after_speaking"],
                ),
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
    hass.services.async_register(
        DOMAIN, SERVICE_ANNOUNCE, announce, schema=ANNOUNCE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ANSWER_AND_SPEAK,
        answer_and_speak,
        schema=ANSWER_AND_SPEAK_SCHEMA,
    )
    hass.data[DOMAIN][DATA_SERVICES_REGISTERED] = True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {DATA_SERVICES_REGISTERED: False})
    _register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: UniFiTalkConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {DATA_SERVICES_REGISTERED: False})
    _register_services(hass)

    try:
        await get_addon_info(hass, ADDON_SLUG)
    except SupervisorError as err:
        raise ConfigEntryNotReady(
            f"ha-sip add-on is unavailable or the Supervisor API cannot be reached: {err}"
        ) from err

    config = _merge_entry_config(entry)
    entry.runtime_data = UniFiTalkRuntimeData(config=config)

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    webhook_id = config.get(CONF_WEBHOOK_ID)
    if not webhook_id:
        raise ConfigEntryNotReady("Missing webhook ID in config entry data")

    async def _handle_webhook(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        del webhook_id
        try:
            payload = await request.json()
        except ValueError:
            return web.Response(status=400, text="Expected JSON payload")

        dispatch_payload = _update_runtime_from_webhook(entry.runtime_data, payload)
        async_dispatcher_send(
            hass, f"{SIGNAL_CALL_STATE}_{entry.entry_id}", dispatch_payload
        )
        hass.bus.async_fire(EVENT_WEBHOOK, payload)
        return web.Response(status=200)

    try:
        webhook_comp.async_unregister(hass, webhook_id)
    except ValueError:
        pass

    webhook_comp.async_register(hass, DOMAIN, "UniFi Talk", webhook_id, _handle_webhook)

    try:
        await set_system_managed(hass, entry.entry_id)
    except SupervisorError as err:
        _LOGGER.debug("Unable to mark ha-sip add-on as system managed: %s", err)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: UniFiTalkConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    webhook_id = entry.runtime_data.config.get(CONF_WEBHOOK_ID)
    if webhook_id:
        try:
            webhook_comp.async_unregister(hass, webhook_id)
        except ValueError:
            pass

    return True


async def _async_reload_entry(hass: HomeAssistant, entry: UniFiTalkConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def get_notify_defaults(entry: ConfigEntry) -> dict[str, Any]:
    config = _merge_entry_config(entry)
    return {
        "target": config.get(CONF_DEFAULT_TARGET, ""),
        "ring_timeout": config.get(CONF_NOTIFY_RING_TIMEOUT, DEFAULT_NOTIFY_RING_TIMEOUT),
        "sip_account": config.get(CONF_NOTIFY_SIP_ACCOUNT, DEFAULT_NOTIFY_SIP_ACCOUNT),
        "hangup_after_message": config.get(CONF_NOTIFY_HANGUP, True),
    }
