from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import HomeAssistant
from homeassistant.components import webhook as webhook_comp

from .const import (
    DOMAIN, CONF_SIP_HOST, CONF_SIP_PORT, CONF_USERNAME, CONF_PASSWORD, CONF_REALM,
    CONF_TTS_ENGINE_ID, CONF_TTS_LANGUAGE, CONF_TTS_VOICE, CONF_TTS_DEBUG,
    CONF_WEBHOOK_ID, CONF_ANSWER_MODE, CONF_SETTLE_TIME, CONF_INCOMING_FILE,
    CONF_CACHE_DIR, CONF_NAME_SERVER, CONF_GLOBAL_OPTIONS, CONF_SIP_OPTIONS,
    CONF_ENABLE_SSH, CONF_SSH_HOST, CONF_SSH_PORT, CONF_SSH_USER, CONF_SSH_PASSWORD
)
from .supervisor import (
    SupervisorError, get_addon_info, validate_addon_options, set_addon_options,
    restart_addon, set_system_managed
)

DEFAULTS = {
    CONF_SIP_HOST: "192.168.1.1",
    CONF_SIP_PORT: 5060,
    CONF_USERNAME: "0001",
    CONF_PASSWORD: "",
    CONF_REALM: "*",
    CONF_ANSWER_MODE: "listen",     # or "accept"
    CONF_SETTLE_TIME: 1,
    CONF_INCOMING_FILE: "",

    CONF_TTS_ENGINE_ID: "tts.home_assistant_cloud",
    CONF_TTS_LANGUAGE: "en",
    CONF_TTS_VOICE: "",
    CONF_TTS_DEBUG: False,

    CONF_WEBHOOK_ID: "",            # if empty we’ll generate one

    CONF_CACHE_DIR: "/config/audio_cache",
    CONF_NAME_SERVER: "",
    CONF_GLOBAL_OPTIONS: "",
    CONF_SIP_OPTIONS: "",

    CONF_ENABLE_SSH: False,
    CONF_SSH_HOST: "",
    CONF_SSH_PORT: 22,
    CONF_SSH_USER: "root",
    CONF_SSH_PASSWORD: "",
}

def _schema(user_input=None):
    u = user_input or {}
    return vol.Schema({
        vol.Required(CONF_SIP_HOST, default=u.get(CONF_SIP_HOST, DEFAULTS[CONF_SIP_HOST])): str,
        vol.Required(CONF_SIP_PORT, default=u.get(CONF_SIP_PORT, DEFAULTS[CONF_SIP_PORT])): int,
        vol.Required(CONF_USERNAME, default=u.get(CONF_USERNAME, DEFAULTS[CONF_USERNAME])): str,
        vol.Optional(CONF_PASSWORD, default=u.get(CONF_PASSWORD, DEFAULTS[CONF_PASSWORD])): str,
        vol.Required(CONF_REALM, default=u.get(CONF_REALM, DEFAULTS[CONF_REALM])): str,
        vol.Required(CONF_ANSWER_MODE, default=u.get(CONF_ANSWER_MODE, DEFAULTS[CONF_ANSWER_MODE])): vol.In(["listen", "accept"]),
        vol.Required(CONF_SETTLE_TIME, default=u.get(CONF_SETTLE_TIME, DEFAULTS[CONF_SETTLE_TIME])): int,
        vol.Optional(CONF_INCOMING_FILE, default=u.get(CONF_INCOMING_FILE, DEFAULTS[CONF_INCOMING_FILE])): str,

        vol.Required(CONF_TTS_ENGINE_ID, default=u.get(CONF_TTS_ENGINE_ID, DEFAULTS[CONF_TTS_ENGINE_ID])): str,
        vol.Required(CONF_TTS_LANGUAGE, default=u.get(CONF_TTS_LANGUAGE, DEFAULTS[CONF_TTS_LANGUAGE])): str,
        vol.Optional(CONF_TTS_VOICE, default=u.get(CONF_TTS_VOICE, DEFAULTS[CONF_TTS_VOICE])): str,
        vol.Optional(CONF_TTS_DEBUG, default=u.get(CONF_TTS_DEBUG, DEFAULTS[CONF_TTS_DEBUG])): bool,

        vol.Optional(CONF_WEBHOOK_ID, default=u.get(CONF_WEBHOOK_ID, DEFAULTS[CONF_WEBHOOK_ID])): str,

        vol.Required(CONF_CACHE_DIR, default=u.get(CONF_CACHE_DIR, DEFAULTS[CONF_CACHE_DIR])): str,
        vol.Optional(CONF_NAME_SERVER, default=u.get(CONF_NAME_SERVER, DEFAULTS[CONF_NAME_SERVER])): str,
        vol.Optional(CONF_GLOBAL_OPTIONS, default=u.get(CONF_GLOBAL_OPTIONS, DEFAULTS[CONF_GLOBAL_OPTIONS])): str,
        vol.Optional(CONF_SIP_OPTIONS, default=u.get(CONF_SIP_OPTIONS, DEFAULTS[CONF_SIP_OPTIONS])): str,

        vol.Optional(CONF_ENABLE_SSH, default=u.get(CONF_ENABLE_SSH, DEFAULTS[CONF_ENABLE_SSH])): bool,
        vol.Optional(CONF_SSH_HOST, default=u.get(CONF_SSH_HOST, DEFAULTS[CONF_SSH_HOST])): str,
        vol.Optional(CONF_SSH_PORT, default=u.get(CONF_SSH_PORT, DEFAULTS[CONF_SSH_PORT])): int,
        vol.Optional(CONF_SSH_USER, default=u.get(CONF_SSH_USER, DEFAULTS[CONF_SSH_USER])): str,
        vol.Optional(CONF_SSH_PASSWORD, default=u.get(CONF_SSH_PASSWORD, DEFAULTS[CONF_SSH_PASSWORD])): str,
    })

class Flow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            # 0) Ensure add-on exists (installed) and reachable
            try:
                info = await get_addon_info(self.hass)  # raises if missing
                if not info or info.get("state") not in ("started", "stopped"):
                    errors["base"] = "addon_missing"
            except SupervisorError:
                errors["base"] = "addon_missing"

            # 1) Optional SSH password fetch for UniFi Talk
            if not errors and user_input.get(CONF_ENABLE_SSH) and not user_input.get(CONF_PASSWORD):
                pwd = await _maybe_fetch_password_over_ssh(self.hass, user_input)
                if not pwd:
                    errors["base"] = "ssh_password_fetch_failed"
                else:
                    user_input[CONF_PASSWORD] = pwd

            # 2) Webhook id (auto-generate if empty)
            if not errors:
                if not (user_input.get(CONF_WEBHOOK_ID) or "").strip():
                    # generate a webhook id and register (no handler; ha-sip will POST to it)
                    user_input[CONF_WEBHOOK_ID] = webhook_comp.async_generate_id()
                # Ensure URL is registered, even with no-op handler, so it shows in UI
                def _noop_webhook(hass: HomeAssistant, webhook_id: str, request):
                    return
                try:
                    webhook_comp.async_register(
                        self.hass, DOMAIN, "ha-sip", user_input[CONF_WEBHOOK_ID], _noop_webhook
                    )
                except Exception:
                    # If already registered, that's fine.
                    pass

            # 3) Build ha-sip options and write
            if not errors:
                host = user_input[CONF_SIP_HOST]
                port = user_input[CONF_SIP_PORT]
                username = user_input[CONF_USERNAME]
                password = user_input.get(CONF_PASSWORD, "")
                registrar_uri = f"sip:{host}"
                id_uri = f"sip:{username}@{host}"
                sip_options = user_input.get(CONF_SIP_OPTIONS, "").strip()
                global_opts = user_input.get(CONF_GLOBAL_OPTIONS, "").strip()

                options = {
                    "sip_global": {
                        "port": port,
                        "log_level": 5,
                        "name_server": user_input.get(CONF_NAME_SERVER, ""),
                        "cache_dir": user_input.get(CONF_CACHE_DIR, "/config/audio_cache"),
                        "global_options": global_opts,
                    },
                    "sip": {
                        "enabled": True,
                        "registrar_uri": registrar_uri,
                        "id_uri": id_uri,
                        "realm": user_input.get(CONF_REALM, "*"),
                        "user_name": username,
                        "password": password,
                        "answer_mode": user_input.get(CONF_ANSWER_MODE, "listen"),
                        "settle_time": user_input.get(CONF_SETTLE_TIME, 1),
                        "incoming_call_file": user_input.get(CONF_INCOMING_FILE, ""),
                        "options": sip_options,
                    },
                    "tts": {
                        "engine_id": user_input[CONF_TTS_ENGINE_ID],
                        "language": user_input.get(CONF_TTS_LANGUAGE, "en"),
                        "voice": user_input.get(CONF_TTS_VOICE, ""),
                        "debug_print": bool(user_input.get(CONF_TTS_DEBUG, False)),
                    },
                    "webhook": {
                        "id": user_input[CONF_WEBHOOK_ID],
                    },
                }
                try:
                    await validate_addon_options(self.hass, options)
                    await set_addon_options(self.hass, options)
                    await restart_addon(self.hass)
                except SupervisorError:
                    errors["base"] = "addon_options_failed"

            # 4) Finish
            if not errors:
                entry = await self.async_set_unique_id("hacs_unifi_talk_singleton")
                self._abort_if_unique_id_configured()
                entry = await self.async_create_entry(title="UniFi Talk (ha-sip)", data=user_input)
                try:
                    await set_system_managed(self.hass, entry.entry_id)
                except SupervisorError:
                    pass
                return entry

        return self.async_show_form(step_id="user", data_schema=_schema(user_input), errors=errors)

    async def async_get_options_flow(self, config_entry):
        return OptionsFlow(config_entry)

class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # Try to write and restart add-on with updated options
            try:
                host = user_input[CONF_SIP_HOST]
                port = user_input[CONF_SIP_PORT]
                username = user_input[CONF_USERNAME]
                registrar_uri = f"sip:{host}"
                id_uri = f"sip:{username}@{host}"
                options = {
                    "sip_global": {
                        "port": port,
                        "log_level": 5,
                        "name_server": user_input.get(CONF_NAME_SERVER, ""),
                        "cache_dir": user_input.get(CONF_CACHE_DIR, "/config/audio_cache"),
                        "global_options": user_input.get(CONF_GLOBAL_OPTIONS, "").strip(),
                    },
                    "sip": {
                        "enabled": True,
                        "registrar_uri": registrar_uri,
                        "id_uri": id_uri,
                        "realm": user_input.get(CONF_REALM, "*"),
                        "user_name": username,
                        "password": user_input.get(CONF_PASSWORD, self.entry.data.get(CONF_PASSWORD, "")),
                        "answer_mode": user_input.get(CONF_ANSWER_MODE, "listen"),
                        "settle_time": user_input.get(CONF_SETTLE_TIME, 1),
                        "incoming_call_file": user_input.get(CONF_INCOMING_FILE, ""),
                        "options": user_input.get(CONF_SIP_OPTIONS, "").strip(),
                    },
                    "tts": {
                        "engine_id": user_input[CONF_TTS_ENGINE_ID],
                        "language": user_input.get(CONF_TTS_LANGUAGE, "en"),
                        "voice": user_input.get(CONF_TTS_VOICE, ""),
                        "debug_print": bool(user_input.get(CONF_TTS_DEBUG, False)),
                    },
                    "webhook": {
                        "id": user_input[CONF_WEBHOOK_ID],
                    },
                }
                await validate_addon_options(self.hass, options)
                await set_addon_options(self.hass, options)
                await restart_addon(self.hass)
            except SupervisorError:
                return self.async_show_form(step_id="init", data_schema=_schema(user_input or self.entry.options), errors={"base": "addon_options_failed"})
            return self.async_create_entry(title="", data=user_input)

        # prefill
        merged = {**DEFAULTS, **self.entry.data, **(self.entry.options or {})}
        return self.async_show_form(step_id="init", data_schema=_schema(merged))

# ---------- SSH helper ----------
async def _maybe_fetch_password_over_ssh(hass: HomeAssistant, data: dict) -> str | None:
    import paramiko
    host = data[CONF_SSH_HOST]
    port = data.get(CONF_SSH_PORT, 22)
    user = data.get(CONF_SSH_USER, "root")
    pw = data[CONF_SSH_PASSWORD]
    ext = data[CONF_USERNAME]
    cmd = f"fs_cli -x 'user_data {ext}@talk.com param password'"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        await hass.async_add_executor_job(client.connect, host, port, user, pw, 10.0)
        stdin, stdout, stderr = await hass.async_add_executor_job(client.exec_command, cmd)
        out = await hass.async_add_executor_job(stdout.read)
        err = await hass.async_add_executor_job(stderr.read)
        result = (out or b"").decode().strip()
        if not result or err:
            return None
        return result.splitlines()[-1].strip()
    finally:
        client.close()
# ---------- end SSH helper ----------