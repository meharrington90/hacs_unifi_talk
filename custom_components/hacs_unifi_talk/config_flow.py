from __future__ import annotations

from functools import partial
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import webhook as webhook_comp
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    ADDON_SLUG,
    CONF_ANSWER_MODE,
    CONF_CACHE_DIR,
    CONF_DEFAULT_TARGET,
    CONF_ENABLE_SSH,
    CONF_GLOBAL_OPTIONS,
    CONF_INCOMING_FILE,
    CONF_NAME_SERVER,
    CONF_NOTIFY_HANGUP,
    CONF_NOTIFY_RING_TIMEOUT,
    CONF_NOTIFY_SIP_ACCOUNT,
    CONF_PASSWORD,
    CONF_REALM,
    CONF_SETTLE_TIME,
    CONF_SIP_HOST,
    CONF_SIP_OPTIONS,
    CONF_SIP_PORT,
    CONF_SSH_HOST,
    CONF_SSH_PASSWORD,
    CONF_SSH_PORT,
    CONF_SSH_USER,
    CONF_TTS_DEBUG,
    CONF_TTS_ENGINE_ID,
    CONF_TTS_LANGUAGE,
    CONF_TTS_VOICE,
    CONF_USERNAME,
    CONF_WEBHOOK_ID,
    DEFAULT_ANSWER_MODE,
    DEFAULT_CACHE_DIR,
    DEFAULT_NOTIFY_RING_TIMEOUT,
    DEFAULT_NOTIFY_SIP_ACCOUNT,
    DEFAULT_SETTLE_TIME,
    DEFAULT_SIP_HOST,
    DEFAULT_SIP_PORT,
    DEFAULT_SSH_PORT,
    DEFAULT_TTS_ENGINE_ID,
    DEFAULT_TTS_LANGUAGE,
    DOMAIN,
    NOTIFY_OPTION_KEYS,
    REQUIRED_SIP_OPTION,
)
from .supervisor import (
    SupervisorError,
    get_addon_info,
    restart_addon,
    set_addon_options,
    validate_addon_options,
)

DEFAULTS = {
    CONF_SIP_HOST: DEFAULT_SIP_HOST,
    CONF_SIP_PORT: DEFAULT_SIP_PORT,
    CONF_USERNAME: "0001",
    CONF_PASSWORD: "",
    CONF_REALM: "*",
    CONF_ANSWER_MODE: DEFAULT_ANSWER_MODE,
    CONF_SETTLE_TIME: DEFAULT_SETTLE_TIME,
    CONF_INCOMING_FILE: "",
    CONF_TTS_ENGINE_ID: DEFAULT_TTS_ENGINE_ID,
    CONF_TTS_LANGUAGE: DEFAULT_TTS_LANGUAGE,
    CONF_TTS_VOICE: "",
    CONF_TTS_DEBUG: False,
    CONF_WEBHOOK_ID: "",
    CONF_DEFAULT_TARGET: "",
    CONF_NOTIFY_RING_TIMEOUT: DEFAULT_NOTIFY_RING_TIMEOUT,
    CONF_NOTIFY_SIP_ACCOUNT: DEFAULT_NOTIFY_SIP_ACCOUNT,
    CONF_NOTIFY_HANGUP: True,
    CONF_CACHE_DIR: DEFAULT_CACHE_DIR,
    CONF_NAME_SERVER: "",
    CONF_GLOBAL_OPTIONS: "",
    CONF_SIP_OPTIONS: REQUIRED_SIP_OPTION,
    CONF_ENABLE_SSH: False,
    CONF_SSH_HOST: DEFAULT_SIP_HOST,
    CONF_SSH_PORT: DEFAULT_SSH_PORT,
    CONF_SSH_USER: "root",
    CONF_SSH_PASSWORD: "",
}

CORE_CONFIG_KEYS: tuple[str, ...] = (
    CONF_SIP_HOST,
    CONF_SIP_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REALM,
    CONF_ANSWER_MODE,
    CONF_SETTLE_TIME,
    CONF_INCOMING_FILE,
    CONF_TTS_ENGINE_ID,
    CONF_TTS_LANGUAGE,
    CONF_TTS_VOICE,
    CONF_TTS_DEBUG,
    CONF_WEBHOOK_ID,
    CONF_CACHE_DIR,
    CONF_NAME_SERVER,
    CONF_GLOBAL_OPTIONS,
    CONF_SIP_OPTIONS,
    CONF_ENABLE_SSH,
    CONF_SSH_HOST,
    CONF_SSH_PORT,
    CONF_SSH_USER,
    CONF_SSH_PASSWORD,
)

NON_EMPTY_STRING = vol.All(cv.string, vol.Length(min=1))


def _config_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    values = {**DEFAULTS, **(user_input or {})}
    return vol.Schema(
        {
            vol.Required(
                CONF_SIP_HOST, default=values[CONF_SIP_HOST]
            ): NON_EMPTY_STRING,
            vol.Required(CONF_SIP_PORT, default=values[CONF_SIP_PORT]): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Required(
                CONF_USERNAME, default=values[CONF_USERNAME]
            ): NON_EMPTY_STRING,
            vol.Optional(CONF_PASSWORD, default=values[CONF_PASSWORD]): cv.string,
            vol.Required(CONF_REALM, default=values[CONF_REALM]): NON_EMPTY_STRING,
            vol.Required(
                CONF_ANSWER_MODE, default=values[CONF_ANSWER_MODE]
            ): vol.In(("listen", "accept")),
            vol.Required(
                CONF_SETTLE_TIME, default=values[CONF_SETTLE_TIME]
            ): vol.All(vol.Coerce(int), vol.Range(min=0)),
            vol.Optional(
                CONF_INCOMING_FILE, default=values[CONF_INCOMING_FILE]
            ): cv.string,
            vol.Required(
                CONF_TTS_ENGINE_ID, default=values[CONF_TTS_ENGINE_ID]
            ): NON_EMPTY_STRING,
            vol.Required(
                CONF_TTS_LANGUAGE, default=values[CONF_TTS_LANGUAGE]
            ): NON_EMPTY_STRING,
            vol.Optional(CONF_TTS_VOICE, default=values[CONF_TTS_VOICE]): cv.string,
            vol.Optional(CONF_TTS_DEBUG, default=values[CONF_TTS_DEBUG]): bool,
            vol.Optional(CONF_WEBHOOK_ID, default=values[CONF_WEBHOOK_ID]): cv.string,
            vol.Required(
                CONF_CACHE_DIR, default=values[CONF_CACHE_DIR]
            ): NON_EMPTY_STRING,
            vol.Optional(CONF_NAME_SERVER, default=values[CONF_NAME_SERVER]): cv.string,
            vol.Optional(
                CONF_GLOBAL_OPTIONS, default=values[CONF_GLOBAL_OPTIONS]
            ): cv.string,
            vol.Optional(CONF_SIP_OPTIONS, default=values[CONF_SIP_OPTIONS]): cv.string,
            vol.Optional(CONF_ENABLE_SSH, default=values[CONF_ENABLE_SSH]): bool,
            vol.Optional(CONF_SSH_HOST, default=values[CONF_SSH_HOST]): cv.string,
            vol.Optional(CONF_SSH_PORT, default=values[CONF_SSH_PORT]): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Optional(CONF_SSH_USER, default=values[CONF_SSH_USER]): cv.string,
            vol.Optional(
                CONF_SSH_PASSWORD, default=values[CONF_SSH_PASSWORD]
            ): cv.string,
        }
    )


def _options_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    values = {**DEFAULTS, **(user_input or {})}
    return vol.Schema(
        {
            vol.Optional(
                CONF_DEFAULT_TARGET, default=values[CONF_DEFAULT_TARGET]
            ): cv.string,
            vol.Optional(
                CONF_NOTIFY_RING_TIMEOUT, default=values[CONF_NOTIFY_RING_TIMEOUT]
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(
                CONF_NOTIFY_SIP_ACCOUNT, default=values[CONF_NOTIFY_SIP_ACCOUNT]
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(CONF_NOTIFY_HANGUP, default=values[CONF_NOTIFY_HANGUP]): bool,
        }
    )


def _sanitize_text(value: Any) -> str:
    return (value or "").strip()


def _normalize_input(user_input: dict[str, Any]) -> dict[str, Any]:
    data = {**DEFAULTS, **user_input}

    string_fields = (
        CONF_SIP_HOST,
        CONF_USERNAME,
        CONF_PASSWORD,
        CONF_REALM,
        CONF_INCOMING_FILE,
        CONF_TTS_ENGINE_ID,
        CONF_TTS_LANGUAGE,
        CONF_TTS_VOICE,
        CONF_WEBHOOK_ID,
        CONF_DEFAULT_TARGET,
        CONF_CACHE_DIR,
        CONF_NAME_SERVER,
        CONF_GLOBAL_OPTIONS,
        CONF_SIP_OPTIONS,
        CONF_SSH_HOST,
        CONF_SSH_USER,
        CONF_SSH_PASSWORD,
    )
    for field in string_fields:
        data[field] = _sanitize_text(data.get(field))

    if not data[CONF_SSH_HOST]:
        data[CONF_SSH_HOST] = data[CONF_SIP_HOST]

    data[CONF_SIP_OPTIONS] = _ensure_required_sip_option(data[CONF_SIP_OPTIONS])
    return data


def _ensure_required_sip_option(options: str) -> str:
    normalized = " ".join(options.split())
    if REQUIRED_SIP_OPTION in normalized:
        return normalized
    if not normalized:
        return REQUIRED_SIP_OPTION
    return f"{normalized} {REQUIRED_SIP_OPTION}"


def _merge_entry_input(config_entry: config_entries.ConfigEntry) -> dict[str, Any]:
    merged = dict(config_entry.data)
    for key in NOTIFY_OPTION_KEYS:
        if key in config_entry.options:
            merged[key] = config_entry.options[key]
    return merged


def _split_entry_payload(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    config_data = {key: data[key] for key in CORE_CONFIG_KEYS}
    option_data = {key: data[key] for key in NOTIFY_OPTION_KEYS}
    return config_data, option_data


def _build_addon_options(data: dict[str, Any]) -> dict[str, Any]:
    host = data[CONF_SIP_HOST]
    username = data[CONF_USERNAME]

    return {
        "sip_global": {
            "port": data[CONF_SIP_PORT],
            "log_level": 5,
            "name_server": data[CONF_NAME_SERVER],
            "cache_dir": data[CONF_CACHE_DIR],
            "global_options": data[CONF_GLOBAL_OPTIONS],
        },
        "sip": {
            "enabled": True,
            "registrar_uri": f"sip:{host}",
            "id_uri": f"sip:{username}@{host}",
            "realm": data[CONF_REALM],
            "user_name": username,
            "password": data[CONF_PASSWORD],
            "answer_mode": data[CONF_ANSWER_MODE],
            "settle_time": data[CONF_SETTLE_TIME],
            "incoming_call_file": data[CONF_INCOMING_FILE],
            "options": data[CONF_SIP_OPTIONS],
        },
        "tts": {
            "engine_id": data[CONF_TTS_ENGINE_ID],
            "language": data[CONF_TTS_LANGUAGE],
            "voice": data[CONF_TTS_VOICE],
            "debug_print": bool(data[CONF_TTS_DEBUG]),
        },
        "webhook": {
            "id": data[CONF_WEBHOOK_ID],
        },
    }


def _validate_local_rules(data: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if data[CONF_ANSWER_MODE] == "accept" and not data[CONF_INCOMING_FILE]:
        errors["base"] = "incoming_file_required"
    elif (
        data[CONF_ENABLE_SSH]
        and not data[CONF_PASSWORD]
        and not data[CONF_SSH_PASSWORD]
    ):
        errors["base"] = "ssh_credentials_missing"
    return errors


async def _async_validate_and_apply(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, str]:
    errors = _validate_local_rules(data)
    if errors:
        return errors

    try:
        await get_addon_info(hass, ADDON_SLUG)
    except SupervisorError:
        return {"base": "addon_missing"}

    if data[CONF_ENABLE_SSH] and not data[CONF_PASSWORD]:
        password = await _maybe_fetch_password_over_ssh(hass, data)
        if not password:
            return {"base": "ssh_password_fetch_failed"}
        data[CONF_PASSWORD] = password

    if not data[CONF_WEBHOOK_ID]:
        data[CONF_WEBHOOK_ID] = webhook_comp.async_generate_id()

    try:
        options = _build_addon_options(data)
        await validate_addon_options(hass, options, ADDON_SLUG)
        await set_addon_options(hass, options, ADDON_SLUG)
        await restart_addon(hass, ADDON_SLUG)
    except SupervisorError:
        return {"base": "addon_options_failed"}

    return {}


class Flow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        await self.async_set_unique_id(f"{DOMAIN}_singleton")
        self._abort_if_unique_id_configured()

        if user_input is not None:
            data = _normalize_input(user_input)
            errors = await _async_validate_and_apply(self.hass, data)
            if not errors:
                config_data, option_data = _split_entry_payload(data)
                return self.async_create_entry(
                    title="UniFi Talk",
                    data=config_data,
                    options=option_data,
                )
            user_input = data

        return self.async_show_form(
            step_id="user",
            data_schema=_config_schema(user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        entry = self._get_reconfigure_entry()
        current = _normalize_input(_merge_entry_input(entry))
        errors: dict[str, str] = {}

        if user_input is not None:
            data = _normalize_input({**current, **user_input})
            errors = await _async_validate_and_apply(self.hass, data)
            if not errors:
                await self.async_set_unique_id(f"{DOMAIN}_singleton")
                self._abort_if_unique_id_mismatch()
                config_data, _ = _split_entry_payload(data)
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=config_data,
                )
            current = data

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_config_schema(current),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlow:
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlowWithReload):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        current = _normalize_input(_merge_entry_input(self.config_entry))

        if user_input is not None:
            data = _normalize_input({**current, **user_input})
            option_data = {key: data[key] for key in NOTIFY_OPTION_KEYS}
            return self.async_create_entry(title="", data=option_data)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _options_schema(current), self.config_entry.options
            ),
            errors={},
        )


async def _maybe_fetch_password_over_ssh(
    hass: HomeAssistant, data: dict[str, Any]
) -> str | None:
    import paramiko

    command = f"fs_cli -x 'user_data {data[CONF_USERNAME]}@talk.com param password'"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        connect = partial(
            client.connect,
            hostname=data[CONF_SSH_HOST],
            port=data[CONF_SSH_PORT],
            username=data[CONF_SSH_USER],
            password=data[CONF_SSH_PASSWORD],
            timeout=10.0,
            look_for_keys=False,
            allow_agent=False,
        )
        await hass.async_add_executor_job(connect)

        stdin, stdout, stderr = await hass.async_add_executor_job(
            client.exec_command, command
        )
        del stdin
        await hass.async_add_executor_job(stdout.channel.recv_exit_status)
        output = await hass.async_add_executor_job(stdout.read)
        error = await hass.async_add_executor_job(stderr.read)

        result = output.decode().strip()
        if not result or error:
            return None

        return result.splitlines()[-1].strip()
    except Exception:
        return None
    finally:
        client.close()
