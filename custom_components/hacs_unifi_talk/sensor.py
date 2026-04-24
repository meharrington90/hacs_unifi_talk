from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_ENTRIES, DOMAIN, SIGNAL_CALL_STATE


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([UniFiTalkLastCallSensor(hass, entry)])


class UniFiTalkLastCallSensor(SensorEntity):
    _attr_name = "UniFi Talk Last Call"
    _attr_icon = "mdi:phone"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_last_call"
        self._attr_native_value = "idle"
        self._attr_extra_state_attributes = {}
        self._unsub_dispatcher = None

    async def async_added_to_hass(self) -> None:
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_CALL_STATE}_{self.entry.entry_id}",
            self._handle_push_update,
        )
        self._handle_push_update()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    @callback
    def _handle_push_update(self) -> None:
        runtime = self.hass.data[DOMAIN][DATA_ENTRIES].get(self.entry.entry_id)
        if runtime is None:
            return

        state = runtime.state
        self._attr_native_value = state.get("event") or "idle"
        self._attr_extra_state_attributes = {
            "caller": state.get("caller"),
            "parsed_caller": state.get("parsed_caller"),
            "sip_account": state.get("sip_account"),
            "internal_id": state.get("internal_id"),
            "last_dtmf_digit": state.get("last_dtmf_digit"),
            "last_type": state.get("last_type"),
            "last_message": state.get("last_message"),
            "last_audio_file": state.get("last_audio_file"),
            "updated": state.get("updated"),
        }
        self.async_write_ha_state()
