"""Config flow for TeamSpeak 3 Monitor."""

from __future__ import annotations

from typing import Any, Mapping, override

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    TeamSpeakAuthenticationError,
    TeamSpeakConnectionError,
    TeamSpeakQueryClient,
    TeamSpeakResponseError,
)
from .const import (
    CONF_QUERY_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SERVER_ID,
    CONF_USERNAME,
    CONF_VOICE_PORT,
    DEFAULT_QUERY_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_VOICE_PORT,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)


def _port_selector() -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=1,
            max=65535,
            step=1,
            mode=NumberSelectorMode.BOX,
        )
    )


def _server_id_selector() -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(min=1, step=1, mode=NumberSelectorMode.BOX)
    )


def _connection_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    values = defaults or {}
    server_id = values.get(CONF_SERVER_ID)
    schema: dict[vol.Marker, Any] = {
        vol.Required(CONF_HOST, default=values.get(CONF_HOST, "")): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="hostname")
        ),
        vol.Required(
            CONF_QUERY_PORT, default=values.get(CONF_QUERY_PORT, DEFAULT_QUERY_PORT)
        ): _port_selector(),
        vol.Required(
            CONF_USERNAME, default=values.get(CONF_USERNAME, "")
        ): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="username")
        ),
        vol.Required(
            CONF_PASSWORD, default=values.get(CONF_PASSWORD, "")
        ): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD,
                autocomplete="current-password",
            )
        ),
        vol.Required(
            CONF_VOICE_PORT, default=values.get(CONF_VOICE_PORT, DEFAULT_VOICE_PORT)
        ): _port_selector(),
    }
    schema[
        vol.Optional(
            CONF_SERVER_ID,
            description={"suggested_value": server_id} if server_id else None,
        )
    ] = _server_id_selector()
    return vol.Schema(schema)


def _normalize(data: Mapping[str, Any]) -> dict[str, Any]:
    result = {
        CONF_HOST: str(data[CONF_HOST]).strip(),
        CONF_QUERY_PORT: int(data[CONF_QUERY_PORT]),
        CONF_USERNAME: str(data[CONF_USERNAME]).strip(),
        CONF_PASSWORD: str(data[CONF_PASSWORD]),
        CONF_VOICE_PORT: int(data[CONF_VOICE_PORT]),
    }
    if data.get(CONF_SERVER_ID) not in (None, ""):
        result[CONF_SERVER_ID] = int(data[CONF_SERVER_ID])
    return result


def _unique_id(data: Mapping[str, Any]) -> str:
    selector = (
        f"sid-{data[CONF_SERVER_ID]}"
        if data.get(CONF_SERVER_ID)
        else f"port-{data[CONF_VOICE_PORT]}"
    )
    return f"{str(data[CONF_HOST]).lower()}:{data[CONF_QUERY_PORT]}:{selector}"


async def _validate(data: Mapping[str, Any]) -> str | None:
    api = TeamSpeakQueryClient(
        host=data[CONF_HOST],
        query_port=data[CONF_QUERY_PORT],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        voice_port=data[CONF_VOICE_PORT],
        server_id=data.get(CONF_SERVER_ID),
        timeout=DEFAULT_TIMEOUT,
    )
    try:
        await api.async_get_clients()
    except TeamSpeakAuthenticationError:
        return "invalid_auth"
    except TeamSpeakConnectionError:
        return "cannot_connect"
    except TeamSpeakResponseError:
        return "invalid_server"
    return None


class TeamSpeakConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a TeamSpeak 3 Monitor config flow."""

    VERSION = 1

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry) -> TeamSpeakOptionsFlow:
        return TeamSpeakOptionsFlow()

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _normalize(user_input)
            if error := await _validate(data):
                errors["base"] = error
            else:
                await self.async_set_unique_id(_unique_id(data))
                self._abort_if_unique_id_configured()
                title = f"TeamSpeak 3 · {data[CONF_HOST]}"
                return self.async_create_entry(
                    title=title,
                    data=data,
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema(user_input),
            errors=errors,
        )

    @override
    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                **entry.data,
                CONF_USERNAME: str(user_input[CONF_USERNAME]).strip(),
                CONF_PASSWORD: str(user_input[CONF_PASSWORD]),
            }
            if error := await _validate(data):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: data[CONF_USERNAME],
                        CONF_PASSWORD: data[CONF_PASSWORD],
                    },
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=entry.data[CONF_USERNAME],
                    ): TextSelector(
                        TextSelectorConfig(
                            type=TextSelectorType.TEXT,
                            autocomplete="username",
                        )
                    ),
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(
                            type=TextSelectorType.PASSWORD,
                            autocomplete="current-password",
                        )
                    ),
                }
            ),
            errors=errors,
        )

    @override
    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _normalize(user_input)
            if error := await _validate(data):
                errors["base"] = error
            else:
                unique_id = _unique_id(data)
                duplicate = next(
                    (
                        candidate
                        for candidate in self.hass.config_entries.async_entries(DOMAIN)
                        if candidate.entry_id != entry.entry_id
                        and candidate.unique_id == unique_id
                    ),
                    None,
                )
                if duplicate:
                    errors["base"] = "already_configured"
                else:
                    self.hass.config_entries.async_update_entry(
                        entry, unique_id=unique_id
                    )
                    return self.async_update_reload_and_abort(
                        entry,
                        data=data,
                    )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_connection_schema(user_input or entry.data),
            errors=errors,
        )


class TeamSpeakOptionsFlow(OptionsFlowWithReload):
    """Configure TeamSpeak polling options and reload on save."""

    @override
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=3600,
                            step=1,
                            unit_of_measurement="seconds",
                            mode=NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )
