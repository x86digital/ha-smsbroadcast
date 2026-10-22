"""Poll remaining credits without sending messages."""

import logging
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiError, AuthenticationError, SmsBroadcastClient
from .const import DOMAIN


class SmsBroadcastCoordinator(DataUpdateCoordinator[int]):
    def __init__(self, hass, entry, client: SmsBroadcastClient):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(minutes=60),
        )
        self.client = client

    async def _async_update_data(self) -> int:
        try:
            return await self.client.async_balance()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from None
        except ApiError as err:
            raise UpdateFailed(str(err)) from None
