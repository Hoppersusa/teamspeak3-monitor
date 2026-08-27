"""TeamSpeak 3 Monitor integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .api import TeamSpeakQueryClient
from .const import (
    CONF_QUERY_PORT,
    CONF_SERVER_ID,
    CONF_USERNAME,
    CONF_VOICE_PORT,
    DEFAULT_TIMEOUT,
    PLATFORMS,
)
from .coordinator import TeamSpeakCoordinator

type TeamSpeakConfigEntry = ConfigEntry[TeamSpeakCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TeamSpeakConfigEntry) -> bool:
    """Set up TeamSpeak 3 Monitor from a config entry."""
    server_id = entry.data.get(CONF_SERVER_ID)
    api = TeamSpeakQueryClient(
        host=entry.data[CONF_HOST],
        query_port=entry.data[CONF_QUERY_PORT],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        voice_port=entry.data[CONF_VOICE_PORT],
        server_id=int(server_id) if server_id not in (None, "") else None,
        timeout=DEFAULT_TIMEOUT,
    )
    coordinator = TeamSpeakCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TeamSpeakConfigEntry) -> bool:
    """Unload a TeamSpeak 3 Monitor config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
