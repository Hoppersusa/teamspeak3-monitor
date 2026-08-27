"""Sensor platform for TeamSpeak 3 Monitor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TeamSpeakConfigEntry
from .const import CONF_QUERY_PORT, CONF_SERVER_ID, CONF_VOICE_PORT, DOMAIN
from .coordinator import TeamSpeakCoordinator


async def async_setup_entry(
    hass,
    entry: TeamSpeakConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the online-clients sensor."""
    async_add_entities([TeamSpeakOnlineClientsSensor(entry.runtime_data, entry)])


class TeamSpeakOnlineClientsSensor(
    CoordinatorEntity[TeamSpeakCoordinator], SensorEntity
):
    """Number and names of online TeamSpeak voice clients."""

    _attr_has_entity_name = True
    _attr_translation_key = "online_clients"
    _attr_icon = "mdi:account-voice"
    _attr_native_unit_of_measurement = "users"

    def __init__(
        self,
        coordinator: TeamSpeakCoordinator,
        entry: TeamSpeakConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_online_clients"
        selector = entry.data.get(CONF_SERVER_ID) or entry.data[CONF_VOICE_PORT]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.data[CONF_HOST]}:{entry.data[CONF_QUERY_PORT]}:{selector}")},
            name=entry.title,
            manufacturer="TeamSpeak",
            model="TeamSpeak 3 ServerQuery",
        )

    @property
    def native_value(self) -> int:
        """Return the number of non-query clients online."""
        return len(self.coordinator.data or ())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the client list consumed by the Lovelace card."""
        clients = self.coordinator.data or ()
        return {
            "clients": [client.nickname for client in clients],
            "client_details": [
                {
                    "nickname": client.nickname,
                    "client_id": client.client_id,
                    "channel_id": client.channel_id,
                }
                for client in clients
            ],
            "server": self._entry.data[CONF_HOST],
            "voice_port": self._entry.data[CONF_VOICE_PORT],
            "query_port": self._entry.data[CONF_QUERY_PORT],
            "server_id": self._entry.data.get(CONF_SERVER_ID) or None,
        }
