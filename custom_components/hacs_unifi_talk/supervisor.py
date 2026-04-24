# SPDX-FileCopyrightText: 2025 Michael E. Harrington
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import ADDON_SLUG

SUPERVISOR_BASE = "http://supervisor"


class SupervisorError(Exception):
    """Raised when the Supervisor API cannot fulfill a request."""


def _headers() -> dict[str, str]:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise SupervisorError(
            "Supervisor token not available; Home Assistant OS/Supervised is required."
        )

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def _request(
    hass: HomeAssistant,
    method: str,
    path: str,
    json_body: dict[str, Any] | None = None,
) -> Any:
    session = async_get_clientsession(hass)
    async with session.request(
        method,
        f"{SUPERVISOR_BASE}{path}",
        headers=_headers(),
        json=json_body,
    ) as response:
        if response.status >= 400:
            raise SupervisorError(
                f"{method} {path} failed with status {response.status}: "
                f"{await response.text()}"
            )

        payload = await response.json()

    if isinstance(payload, dict):
        if payload.get("result") == "error":
            raise SupervisorError(
                payload.get("message", "Supervisor API returned an error")
            )
        return payload.get("data", payload)

    return payload


async def get_addon_info(hass: HomeAssistant, slug: str = ADDON_SLUG) -> dict[str, Any]:
    return await _request(hass, "GET", f"/addons/{slug}/info")


async def validate_addon_options(
    hass: HomeAssistant, options: dict[str, Any], slug: str = ADDON_SLUG
) -> dict[str, Any]:
    return await _request(
        hass,
        "POST",
        f"/addons/{slug}/options/validate",
        {"options": options},
    )


async def set_addon_options(
    hass: HomeAssistant, options: dict[str, Any], slug: str = ADDON_SLUG
) -> None:
    await _request(hass, "POST", f"/addons/{slug}/options", {"options": options})


async def start_addon(hass: HomeAssistant, slug: str = ADDON_SLUG) -> None:
    await _request(hass, "POST", f"/addons/{slug}/start")


async def restart_addon(hass: HomeAssistant, slug: str = ADDON_SLUG) -> None:
    await _request(hass, "POST", f"/addons/{slug}/restart")


async def set_system_managed(
    hass: HomeAssistant, config_entry_id: str, slug: str = ADDON_SLUG
) -> None:
    await _request(
        hass,
        "POST",
        f"/addons/{slug}/sys_options",
        {
            "system_managed": True,
            "system_managed_config_entry": config_entry_id,
        },
    )
