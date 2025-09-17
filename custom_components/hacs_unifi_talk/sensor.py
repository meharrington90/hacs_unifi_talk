from __future__ import annotations
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .__init__ import SIGNAL_CALL_STATE

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities([HacsUnifiTalkCallStateSensor(hass, entry)], update_before_add=False)

class HacsUnifiTalkCallStateSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "UniFi Talk Last Call"
    _attr_icon = "mdi:phone"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_call_state"
        self._state = "idle"
        self._attrs = {}

    async def async_added_to_hass(self) -> None:
        self._unsub = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_CALL_STATE}_{self.entry.entry_id}",
            self._handle_push_update,
        )

    async def async_will_remove_from_hass(self) -> None:
        if hasattr(self, "_unsub") and self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_push_update(self) -> None:
        data = self.hass.data[DOMAIN][self.entry.entry_id]["state"]
        self._state = data.get("event") or "idle"
        self._attrs = {
            "caller": data.get("caller"),
            "parsed_caller": data.get("parsed_caller"),
            "sip_account": data.get("sip_account"),
            "internal_id": data.get("internal_id"),
            "last_dtmf_digit": data.get("last_dtmf_digit"),
            "last_type": data.get("last_type"),
            "last_message": data.get("last_message"),
            "last_audio_file": data.get("last_audio_file"),
            "updated": data.get("updated"),
        }
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attrs
