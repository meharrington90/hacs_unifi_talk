from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import UniFiTalkConfigEntry
from .const import SIGNAL_CALL_STATE
from .entity import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: UniFiTalkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    del hass
    async_add_entities(
        [
            UniFiTalkLastEventSensor(entry),
            UniFiTalkActiveCallsSensor(entry),
            UniFiTalkLastCallerSensor(entry),
            UniFiTalkLastDtmfSensor(entry),
        ]
    )


class UniFiTalkBaseSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: UniFiTalkConfigEntry, suffix: str) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_device_info = device_info(entry)
        self._unsub_dispatcher = None

    async def async_added_to_hass(self) -> None:
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_CALL_STATE}_{self.entry.entry_id}",
            self._handle_push_update,
        )
        self._handle_push_update({})

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    @callback
    def _handle_push_update(self, _: dict) -> None:
        raise NotImplementedError


class UniFiTalkLastEventSensor(UniFiTalkBaseSensor):
    _attr_name = "Last Event"
    _attr_icon = "mdi:phone-log"

    def __init__(self, entry: UniFiTalkConfigEntry) -> None:
        super().__init__(entry, "last_event")
        self._attr_native_value = "idle"
        self._attr_extra_state_attributes = {}

    @callback
    def _handle_push_update(self, _: dict) -> None:
        runtime = self.entry.runtime_data
        summary = runtime.summary()
        self._attr_native_value = summary["last_event"]
        self._attr_extra_state_attributes = {
            "updated": summary["last_updated"],
            "last_caller": summary["last_caller"],
            "internal_id": summary["last_internal_id"],
            "last_menu_id": summary["last_menu_id"],
            "last_dtmf_digit": summary["last_dtmf_digit"],
            "last_message": summary["last_message"],
            "last_audio_file": summary["last_audio_file"],
        }
        self.async_write_ha_state()


class UniFiTalkActiveCallsSensor(UniFiTalkBaseSensor):
    _attr_name = "Active Calls"
    _attr_icon = "mdi:phone-in-talk"

    def __init__(self, entry: UniFiTalkConfigEntry) -> None:
        super().__init__(entry, "active_calls")
        self._attr_native_value = 0
        self._attr_extra_state_attributes = {}

    @callback
    def _handle_push_update(self, _: dict) -> None:
        runtime = self.entry.runtime_data
        active_calls = runtime.active_calls()
        self._attr_native_value = len(active_calls)
        self._attr_extra_state_attributes = {
            "active_call_ids": [session.internal_id for session in active_calls],
            "active_calls": [session.to_dict() for session in active_calls[:5]],
            "recent_calls": runtime.recent_call_snapshots(5),
        }
        self.async_write_ha_state()


class UniFiTalkLastCallerSensor(UniFiTalkBaseSensor):
    _attr_name = "Last Caller"
    _attr_icon = "mdi:account-voice"

    def __init__(self, entry: UniFiTalkConfigEntry) -> None:
        super().__init__(entry, "last_caller")
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    @callback
    def _handle_push_update(self, _: dict) -> None:
        runtime = self.entry.runtime_data
        self._attr_native_value = runtime.last_caller
        self._attr_extra_state_attributes = {
            "last_event": runtime.last_event,
            "updated": runtime.last_updated,
            "last_incoming_call": runtime.last_incoming_call,
        }
        self.async_write_ha_state()


class UniFiTalkLastDtmfSensor(UniFiTalkBaseSensor):
    _attr_name = "Last DTMF Digit"
    _attr_icon = "mdi:dialpad"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, entry: UniFiTalkConfigEntry) -> None:
        super().__init__(entry, "last_dtmf_digit")
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    @callback
    def _handle_push_update(self, _: dict) -> None:
        runtime = self.entry.runtime_data
        self._attr_native_value = runtime.last_dtmf_digit
        self._attr_extra_state_attributes = {
            "updated": runtime.last_updated,
            "internal_id": runtime.last_internal_id,
        }
        self.async_write_ha_state()
