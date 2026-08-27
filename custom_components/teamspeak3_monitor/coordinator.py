"""Polling coordinator for TeamSpeak 3 Monitor."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    TeamSpeakAuthenticationError,
    TeamSpeakClient,
    TeamSpeakConnectionError,
    TeamSpeakQueryClient,
    TeamSpeakResponseError,
)
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class TeamSpeakCoordinator(DataUpdateCoordinator[tuple[TeamSpeakClient, ...]]):
    """Coordinate the shared TeamSpeak client-list poll."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: TeamSpeakQueryClient,
    ) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )
        self.api = api

    async def _async_update_data(self) -> tuple[TeamSpeakClient, ...]:
        try:
            return await self.api.async_get_clients()
        except TeamSpeakAuthenticationError as error:
            raise ConfigEntryAuthFailed("ServerQuery authentication failed") from error
        except (TeamSpeakConnectionError, TeamSpeakResponseError) as error:
            raise UpdateFailed(str(error)) from error
