from __future__ import annotations

import os
from typing import Any, Dict, Optional
import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

SUPERVISOR_BASE = "http://supervisor"
ADDON_SLUG = "c7744bff_ha-sip"  # <— ha-sip slug

class SupervisorError(Exception):
    pass

def _headers() -> Dict[str, str]:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise SupervisorError("Supervisor token not available; not a supervised/OS install?")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

async def _request(hass: HomeAssistant, method: str, path: str, json: Optional[dict] = None) -> Any:
    session = async_get_clientsession(hass)
    url = f"{SUPERVISOR_BASE}{path}"
    async with session.request(method, url, headers=_headers(), json=json) as resp:
        if resp.status >= 400:
            raise SupervisorError(f"{method} {path} -> {resp.status}: {await resp.text()}")
        return await resp.json()

async def get_addon_info(hass: HomeAssistant, slug: str = ADDON_SLUG) -> dict:
    return await _request(hass, "GET", f"/addons/{slug}/info")

async def validate_addon_options(hass: HomeAssistant, options: dict, slug: str = ADDON_SLUG) -> dict:
    return await _request(hass, "POST", f"/addons/{slug}/options/validate", options)

async def set_addon_options(hass: HomeAssistant, options: dict, slug: str = ADDON_SLUG) -> None:
    await _request(hass, "POST", f"/addons/{slug}/options", {"options": options})

async def start_addon(hass: HomeAssistant, slug: str = ADDON_SLUG) -> None:
    await _request(hass, "POST", f"/addons/{slug}/start")

async def restart_addon(hass: HomeAssistant, slug: str = ADDON_SLUG) -> None:
    await _request(hass, "POST", f"/addons/{slug}/restart")

async def set_system_managed(hass: HomeAssistant, config_entry_id: str, slug: str = ADDON_SLUG) -> None:
    await _request(
        hass, "POST", f"/addons/{slug}/sys_options",
        {"system_managed": True, "system_managed_config_entry": config_entry_id},
    )
