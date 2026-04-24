from homeassistant.const import Platform

DOMAIN = "hacs_unifi_talk"

PLATFORMS: list[Platform] = [Platform.SENSOR]

ADDON_SLUG = "c7744bff_ha-sip"
EVENT_WEBHOOK = f"{DOMAIN}_webhook"
SIGNAL_CALL_STATE = f"{DOMAIN}_call_state"

DATA_ENTRIES = "entries"
DATA_SERVICES_REGISTERED = "services_registered"

DEFAULT_SIP_HOST = "192.168.1.1"
DEFAULT_SIP_PORT = 5060
DEFAULT_ANSWER_MODE = "listen"
DEFAULT_SETTLE_TIME = 1
DEFAULT_TTS_ENGINE_ID = "tts.home_assistant_cloud"
DEFAULT_TTS_LANGUAGE = "en"
DEFAULT_CACHE_DIR = "/config/hacs-unifi-talk/audio_cache"
DEFAULT_SSH_PORT = 22
REQUIRED_SIP_OPTION = "--ice false"

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
