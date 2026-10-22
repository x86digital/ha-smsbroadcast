"""Home Assistant tests use mocked provider requests; sockets remain disabled."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def custom_integration(enable_custom_integrations):
    """Load our custom integration in the real HA test harness."""


@pytest.fixture
def client():
    with patch(
        "custom_components.smsbroadcast.SmsBroadcastClient", autospec=True
    ) as factory:
        instance = factory.return_value
        instance.async_balance = AsyncMock(return_value=23)
        instance.async_send = AsyncMock()
        yield instance
