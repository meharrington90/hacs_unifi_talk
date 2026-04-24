from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import UniFiTalkConfigEntry
from .const import CALL_EVENT_TYPES, SIGNAL_CALL_STATE
from .entity import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: UniFiTalkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    del hass
    async_add_entities([UniFiTalkCallEventEntity(entry)])


class UniFiTalkCallEventEntity(EventEntity):
    _attr_has_entity_name = True
    _attr_name = "Call Event"
    _attr_icon = "mdi:phone-ring"
    _attr_should_poll = False
    _attr_event_types = list(CALL_EVENT_TYPES)

    def __init__(self, entry: UniFiTalkConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_call_event"
        self._attr_device_info = device_info(entry)
        self._unsub_dispatcher = None

    async def async_added_to_hass(self) -> None:
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_CALL_STATE}_{self.entry.entry_id}",
            self._handle_push_update,
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    @callback
    def _handle_push_update(self, payload: dict) -> None:
        event_type = payload.get("event")
        if event_type not in CALL_EVENT_TYPES:
            return

        self._trigger_event(
            event_type,
            {
                "internal_id": payload.get("internal_id"),
                "parsed_caller": payload.get("parsed_caller"),
                "caller": payload.get("caller"),
                "digit": payload.get("digit"),
                "menu_id": payload.get("menu_id"),
                "sip_account": payload.get("sip_account"),
                "timestamp": payload.get("timestamp"),
            },
        )
        self.async_write_ha_state()
