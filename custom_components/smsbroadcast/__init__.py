"""SMS Broadcast integration: UI configuration, sending and credit balance."""
import voluptuous as vol
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import ApiError, AuthenticationError, SmsBroadcastClient, normalize_recipients
from .const import DOMAIN, CONF_SENDER, CONF_MAXSPLIT, DEFAULT_MAXSPLIT
from .coordinator import SmsBroadcastCoordinator

PLATFORMS = [Platform.SENSOR]
SEND_SCHEMA = vol.Schema({
    vol.Required("to"): vol.Any(cv.string, [cv.string]),
    vol.Required("message"): cv.string,
    vol.Optional("sender"): cv.string,
    vol.Optional("reference", default=""): vol.All(cv.string, vol.Length(max=20)),
    vol.Optional("delay", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
    vol.Optional("maxsplit"): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
})

async def async_setup(hass, config):
    async def send_sms(call):
        entries = [entry for entry in hass.config_entries.async_entries(DOMAIN)
                   if getattr(entry, "runtime_data", None) is not None]
        if len(entries) != 1:
            raise ServiceValidationError("Set up and load the SMS Broadcast integration first.")
        entry = entries[0]
        coordinator = entry.runtime_data
        settings = {**entry.data, **entry.options}
        try:
            recipients = normalize_recipients(call.data["to"])
            results = await coordinator.client.async_send(
                recipients, call.data["message"], call.data.get("sender", settings[CONF_SENDER]),
                call.data["reference"], call.data["delay"],
                call.data.get("maxsplit", settings.get(CONF_MAXSPLIT, DEFAULT_MAXSPLIT)),
            )
        except AuthenticationError as err:
            entry.async_start_reauth(hass)
            raise ServiceValidationError(str(err)) from None
        except (ApiError, ValueError) as err:
            raise ServiceValidationError(str(err)) from None
        # Balance retrieval failure must not turn a successful send into a failed action.
        await coordinator.async_request_refresh()
        accepted = [result for result in results if result.status == "OK"]
        rejected = [result for result in results if result.status == "BAD"]
        if rejected:
            raise ServiceValidationError(
                f"SMS Broadcast accepted {len(accepted)} recipient(s) and rejected {len(rejected)}: "
                + ", ".join(result.recipient for result in rejected)
                + ". Check the portal; retry only rejected recipients."
            )
        return {"accepted": [{"to": result.recipient, "sms_reference": result.sms_reference}
                             for result in accepted]}

    hass.services.async_register(DOMAIN, "send_sms", send_sms, schema=SEND_SCHEMA,
                                 supports_response=SupportsResponse.OPTIONAL)
    return True

async def async_setup_entry(hass, entry):
    client = SmsBroadcastClient(async_get_clientsession(hass), entry.data[CONF_USERNAME],
                                entry.data[CONF_PASSWORD])
    coordinator = SmsBroadcastCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True

async def async_update_options(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass, entry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data = None
    return unloaded
