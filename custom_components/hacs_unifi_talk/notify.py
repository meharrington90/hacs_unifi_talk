# SPDX-FileCopyrightText: 2025 Michael E. Harrington
# SPDX-License-Identifier: MIT

from __future__ import annotations

from homeassistant.components.notify import NotifyEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import UniFiTalkConfigEntry, get_notify_defaults
from .const import DOMAIN
from .entity import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: UniFiTalkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([UniFiTalkNotifyEntity(hass, entry)])


class UniFiTalkNotifyEntity(NotifyEntity):
    _attr_has_entity_name = True
    _attr_name = "Default Target"
    _attr_icon = "mdi:bullhorn"

    def __init__(self, hass: HomeAssistant, entry: UniFiTalkConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_default_target"
        self._attr_device_info = device_info(entry)

    @property
    def available(self) -> bool:
        return bool(get_notify_defaults(self.entry)["target"])

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        defaults = get_notify_defaults(self.entry)
        return {
            "target": defaults["target"],
            "ring_timeout": defaults["ring_timeout"],
            "sip_account": defaults["sip_account"],
            "hangup_after_message": defaults["hangup_after_message"],
        }

    async def async_send_message(
        self, message: str, title: str | None = None
    ) -> None:
        defaults = get_notify_defaults(self.entry)
        if not defaults["target"]:
            raise ServiceValidationError(
                "Set a default target in the UniFi Talk integration options "
                "before using notify."
            )

        await self.hass.services.async_call(
            DOMAIN,
            "announce",
            {
                "number": defaults["target"],
                "message": message,
                "title": title,
                "ring_timeout": defaults["ring_timeout"],
                "sip_account": defaults["sip_account"],
                "hangup_after_speaking": defaults["hangup_after_message"],
            },
            blocking=True,
        )
        self._async_record_notification()
