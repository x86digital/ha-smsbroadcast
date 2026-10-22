"""Offline integration, config flow and action regression tests."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smsbroadcast.api import ApiError, AuthenticationError, SendResult
from custom_components.smsbroadcast.const import DOMAIN

DATA = {"username": "user", "password": "secret", "sender": "", "maxsplit": 5}


async def setup(hass, client):
    entry = MockConfigEntry(
        domain=DOMAIN, title="SMS Broadcast", data=DATA, unique_id=DOMAIN
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def send(hass, **data):
    return await hass.services.async_call(
        DOMAIN,
        "send_sms",
        {"to": "0412345678", "message": "Alarm", **data},
        blocking=True,
        return_response=True,
    )


async def test_setup_sensor_zero_balance_and_unload(hass, client):
    client.async_balance.return_value = 0
    entry = await setup(hass, client)
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_balance"
    )
    state = hass.states.get(entity_id)
    assert state.state == "0"
    assert state.attributes["unit_of_measurement"] == "credits"
    assert entry.state is ConfigEntryState.LOADED
    client.async_send.assert_not_called()
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert getattr(entry, "runtime_data", None) is None
    with pytest.raises(ServiceValidationError, match="Set up and load"):
        await send(hass)


async def test_send_normalization_settings_overrides_and_response(hass, client):
    entry = await setup(hass, client)
    hass.config_entries.async_update_entry(
        entry, options={"sender": "Home", "maxsplit": 2}
    )
    await hass.async_block_till_done()
    client.async_send.return_value = [SendResult("OK", "61412345678", "123")]
    result = await send(hass, to=["0412345678", "+61 412 345 678"])
    assert result == {"accepted": [{"to": "61412345678", "sms_reference": "123"}]}
    client.async_send.assert_awaited_once_with(
        ["61412345678"], "Alarm", "Home", "", 0, 2
    )
    await send(hass, sender="", maxsplit=1, reference="alarm", delay=10)
    client.async_send.assert_awaited_with(["61412345678"], "Alarm", "", "alarm", 10, 1)


async def test_partial_failure_refreshes_balance_without_resending(hass, client):
    await setup(hass, client)
    client.async_send.return_value = [
        SendResult("OK", "61412345678", "123"),
        SendResult("BAD", "61498765432"),
    ]
    client.async_balance.reset_mock()
    with pytest.raises(
        ServiceValidationError, match="accepted 1.*rejected 1: 61498765432"
    ):
        await send(hass, to="0412345678,0498765432")
    client.async_send.assert_awaited_once()
    client.async_balance.assert_awaited_once()


@pytest.mark.parametrize(
    "error", [ApiError("Offline"), AuthenticationError("Rejected")]
)
async def test_accepted_send_survives_balance_failure(hass, client, error):
    entry = await setup(hass, client)
    client.async_send.return_value = [SendResult("OK", "61412345678", "123")]
    client.async_balance.side_effect = error
    result = await send(hass)
    assert len(result["accepted"]) == 1
    assert not entry.runtime_data.last_update_success
    client.async_send.assert_awaited_once()


async def test_send_authentication_starts_reauth_without_retry(hass, client):
    entry = await setup(hass, client)
    client.async_send.side_effect = AuthenticationError("Rejected")
    with patch.object(type(entry), "async_start_reauth") as reauth:
        with pytest.raises(ServiceValidationError, match="Rejected"):
            await send(hass)
        reauth.assert_called_once_with(hass)
    client.async_send.assert_awaited_once()


async def test_setup_auth_and_connection_errors(hass, client):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA)
    entry.add_to_hass(hass)
    client.async_balance.side_effect = ApiError("Offline")
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    client.async_send.assert_not_called()


async def test_user_flow_and_single_instance(hass):
    with patch(
        "custom_components.smsbroadcast.config_flow.SmsBroadcastClient", autospec=True
    ) as factory:
        factory.return_value.async_balance = AsyncMock(return_value=0)
        with patch(
            "custom_components.smsbroadcast.async_setup_entry", return_value=True
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "user"}
            )
            assert result["type"] == "form"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], DATA
            )
            assert result["type"] == "create_entry"
            assert result["data"] == DATA
            await hass.async_block_till_done()
        factory.return_value.async_balance.assert_awaited_once()
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["reason"] == "single_instance_allowed"


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (AuthenticationError("bad"), "invalid_auth"),
        (ApiError("offline"), "cannot_connect"),
    ],
)
async def test_user_flow_errors(hass, error, expected):
    with patch(
        "custom_components.smsbroadcast.config_flow.SmsBroadcastClient", autospec=True
    ) as factory:
        factory.return_value.async_balance = AsyncMock(side_effect=error)
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], DATA)
        assert result["errors"] == {"base": expected}


async def test_options_and_reauthentication(hass, client):
    entry = await setup(hass, client)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"sender": "Home Alarm", "maxsplit": 2}
    )
    assert result["errors"] == {"base": "invalid_sender"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"sender": "Home", "maxsplit": 2}
    )
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert entry.options == {"sender": "Home", "maxsplit": 2}
    with patch(
        "custom_components.smsbroadcast.config_flow.SmsBroadcastClient", autospec=True
    ) as factory:
        factory.return_value.async_balance = AsyncMock(return_value=23)
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
            data=entry.data,
        )
        assert result["step_id"] == "reauth_confirm"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"password": "new"}
        )
        assert result["reason"] == "reauth_successful"
        await hass.async_block_till_done()
    assert entry.data["password"] == "new"
    assert entry.options["sender"] == "Home"


async def test_balance_failure_marks_sensor_unavailable_then_recovers(hass, client):
    entry = await setup(hass, client)
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_balance"
    )
    client.async_balance.side_effect = ApiError("Offline")
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "unavailable"
    client.async_balance.side_effect = None
    client.async_balance.return_value = 12
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "12"
    assert entry.runtime_data.update_interval.total_seconds() == 3600
    client.async_send.assert_not_called()


async def test_setup_authentication_failure_requests_reauth(hass, client):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA)
    entry.add_to_hass(hass)
    client.async_balance.side_effect = AuthenticationError("Rejected")
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(flow["context"]["source"] == "reauth" for flow in flows)
    client.async_send.assert_not_called()


async def test_invalid_recipient_never_calls_send(hass, client):
    await setup(hass, client)
    with pytest.raises(ServiceValidationError):
        await send(hass, to=["0412345678", "not a number"])
    client.async_send.assert_not_called()
