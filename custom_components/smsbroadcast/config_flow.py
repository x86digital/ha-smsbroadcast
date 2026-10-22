"""UI setup, options and credential recovery."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ApiError, AuthenticationError, SmsBroadcastClient, validate_sender
from .const import CONF_MAXSPLIT, CONF_SENDER, DEFAULT_MAXSPLIT, DOMAIN, NAME

PASSWORD = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)


def settings_schema(settings=None):
    settings = settings or {}
    return vol.Schema(
        {
            vol.Optional(CONF_SENDER, default=settings.get(CONF_SENDER, "")): str,
            vol.Required(
                CONF_MAXSPLIT, default=settings.get(CONF_MAXSPLIT, DEFAULT_MAXSPLIT)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
        }
    )


async def validate(hass, data):
    try:
        validate_sender(data.get(CONF_SENDER, ""))
    except ValueError:
        return "invalid_sender"
    try:
        await SmsBroadcastClient(
            async_get_clientsession(hass), data[CONF_USERNAME], data[CONF_PASSWORD]
        ).async_balance()
    except AuthenticationError:
        return "invalid_auth"
    except ApiError:
        return "cannot_connect"
    return None


class SmsBroadcastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SmsBroadcastOptionsFlow()

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        errors = {}
        if user_input is not None:
            user_input = {
                **user_input,
                CONF_USERNAME: user_input[CONF_USERNAME].strip(),
            }
            error = await validate(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=NAME, data=user_input)
        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): vol.All(str, vol.Length(min=1)),
                vol.Required(CONF_PASSWORD): PASSWORD,
                **settings_schema().schema,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            data = {**entry.data, **user_input}
            error = await validate(self.hass, data)
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates=user_input
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): PASSWORD,
                }
            ),
            errors=errors,
        )


class SmsBroadcastOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                validate_sender(user_input[CONF_SENDER])
            except ValueError:
                errors["base"] = "invalid_sender"
            else:
                return self.async_create_entry(title="", data=user_input)
        settings = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=settings_schema(settings), errors=errors
        )
