from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_ADDON

DATA_SCHEMA = vol.Schema({
    vol.Optional(CONF_HOST, default="192.168.1.1"): str,
    vol.Optional(CONF_PORT, default=5060): int,
    vol.Optional(CONF_ADDON, default="89275b70_dss_voip"): str,
})

class DSSVoipConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title="DSS VoIP", data=user_input)
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

    async def async_step_import(self, user_input=None) -> FlowResult:
        return await self.async_step_user(user_input)

    async def async_step_reauth(self, user_input=None) -> FlowResult:
        return await self.async_step_user(user_input)

    async def async_get_options_flow(self, config_entry):
        return DSSVoipOptionsFlow(config_entry)

class DSSVoipOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        data = {**self.entry.data, **(self.entry.options or {})}
        schema = vol.Schema({
            vol.Optional(CONF_HOST, default=data.get(CONF_HOST, "192.168.1.1")): str,
            vol.Optional(CONF_PORT, default=data.get(CONF_PORT, 5060)): int,
            vol.Optional(CONF_ADDON, default=data.get(CONF_ADDON, "89275b70_dss_voip")): str,
        })
        return self.async_show_form(step_id="init", data_schema=schema)
