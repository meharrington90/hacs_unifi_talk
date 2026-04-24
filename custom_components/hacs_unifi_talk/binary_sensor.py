from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
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
    async_add_entities([UniFiTalkCallInProgressBinarySensor(entry)])


class UniFiTalkCallInProgressBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Call In Progress"
    _attr_icon = "mdi:phone-in-talk"
    _attr_should_poll = False

    def __init__(self, entry: UniFiTalkConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_call_in_progress"
        self._attr_device_info = device_info(entry)
        self._attr_is_on = False
        self._attr_extra_state_attributes = {}
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
        active_calls = self.entry.runtime_data.active_calls()
        self._attr_is_on = bool(active_calls)
        self._attr_extra_state_attributes = {
            "active_call_count": len(active_calls),
            "active_call_ids": [session.internal_id for session in active_calls],
            "last_event": self.entry.runtime_data.last_event,
            "updated": self.entry.runtime_data.last_updated,
        }
        self.async_write_ha_state()
