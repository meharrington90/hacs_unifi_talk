from homeassistant.const import Platform

DOMAIN = "hacs_unifi_talk"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.EVENT,
    Platform.NOTIFY,
]

ADDON_SLUG = "c7744bff_ha-sip"
EVENT_WEBHOOK = f"{DOMAIN}_webhook"
SIGNAL_CALL_STATE = f"{DOMAIN}_call_state"

DATA_SERVICES_REGISTERED = "services_registered"
STORAGE_KEY = f"{DOMAIN}_runtime"
STORAGE_VERSION = 1

DEFAULT_SIP_HOST = "192.168.1.1"
DEFAULT_SIP_PORT = 5060
DEFAULT_ANSWER_MODE = "listen"
DEFAULT_SETTLE_TIME = 1
DEFAULT_TTS_ENGINE_ID = "tts.home_assistant_cloud"
DEFAULT_TTS_LANGUAGE = "en"
DEFAULT_CACHE_DIR = "/config/hacs-unifi-talk/audio_cache"
DEFAULT_SSH_PORT = 22
DEFAULT_NOTIFY_RING_TIMEOUT = 15
DEFAULT_NOTIFY_SIP_ACCOUNT = 1
REQUIRED_SIP_OPTION = "--ice false"

CALL_EVENT_TYPES: tuple[str, ...] = (
    "incoming_call",
    "call_established",
    "entered_menu",
    "dtmf_digit",
    "playback_done",
    "ring_timeout",
    "timeout",
    "call_disconnected",
)
TERMINAL_CALL_EVENTS: tuple[str, ...] = (
    "ring_timeout",
    "timeout",
    "call_disconnected",
)

# Core SIP / TTS
CONF_SIP_HOST = "sip_host"
CONF_SIP_PORT = "sip_port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_REALM = "realm"
CONF_ANSWER_MODE = "answer_mode"
CONF_SETTLE_TIME = "settle_time"
CONF_INCOMING_FILE = "incoming_call_file"

CONF_TTS_ENGINE_ID = "tts_engine_id"
CONF_TTS_LANGUAGE = "tts_language"
CONF_TTS_VOICE = "tts_voice"
CONF_TTS_DEBUG = "tts_debug_print"

# Webhook
CONF_WEBHOOK_ID = "webhook_id"

# Notify / announcement helpers
CONF_DEFAULT_TARGET = "default_target"
CONF_NOTIFY_RING_TIMEOUT = "notify_ring_timeout"
CONF_NOTIFY_SIP_ACCOUNT = "notify_sip_account"
CONF_NOTIFY_HANGUP = "notify_hangup_after_message"
NOTIFY_OPTION_KEYS: tuple[str, ...] = (
    CONF_DEFAULT_TARGET,
    CONF_NOTIFY_RING_TIMEOUT,
    CONF_NOTIFY_SIP_ACCOUNT,
    CONF_NOTIFY_HANGUP,
)

# Global
CONF_CACHE_DIR = "cache_dir"
CONF_NAME_SERVER = "name_server"
CONF_GLOBAL_OPTIONS = "global_options"
CONF_SIP_OPTIONS = "sip_options"

# SSH (optional)
CONF_ENABLE_SSH = "enable_ssh"
CONF_SSH_HOST = "ssh_host"
CONF_SSH_PORT = "ssh_port"
CONF_SSH_USER = "ssh_user"
CONF_SSH_PASSWORD = "ssh_password"
