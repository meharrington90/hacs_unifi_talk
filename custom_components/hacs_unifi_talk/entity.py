from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

DEVICE_MANUFACTURER = "Ubiquiti"
DEVICE_MODEL = "UniFi Talk via ha-sip"
DEVICE_NAME = "UniFi Talk"


def device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=DEVICE_MANUFACTURER,
        model=DEVICE_MODEL,
        name=DEVICE_NAME,
    )


def async_ensure_device(hass: HomeAssistant, entry: ConfigEntry) -> str:
    registry = dr.async_get(hass)
    device = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=DEVICE_MANUFACTURER,
        model=DEVICE_MODEL,
        name=DEVICE_NAME,
    )
    return device.id
