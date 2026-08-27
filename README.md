# TeamSpeak 3 Monitor

A Home Assistant custom integration that polls a TeamSpeak 3 ServerQuery endpoint and exposes connected voice clients as a sensor. It is adapted from [MMM-teamspeak3](https://github.com/Thlb/MMM-teamspeak3).

## Features

- UI-based configuration with no YAML credentials.
- Selects a virtual server by voice port or server ID.
- Filters ServerQuery connections from the client list.
- Configurable polling interval and reauthentication flow.
- Exposes online count, client names, channel IDs, and server details.
- Keeps the ServerQuery username and password out of entity attributes.

## Requirements

- Home Assistant 2026.6 or newer is recommended.
- A reachable TeamSpeak 3 raw ServerQuery endpoint, normally TCP port `10011`.
- A least-privilege ServerQuery account allowed to select the server and run `clientlist`.

## Install with HACS

1. Open HACS in Home Assistant.
2. Open the three-dot menu and select **Custom repositories**.
3. Add `https://github.com/Hoppersusa/teamspeak3-monitor` with category **Integration**.
4. Download **TeamSpeak 3 Monitor**.
5. Restart Home Assistant.
6. Open **Settings → Devices & services → Add integration** and search for **TeamSpeak 3 Monitor**.

## Manual installation

Copy `custom_components/teamspeak3_monitor` into the `custom_components` directory under your Home Assistant configuration directory, then restart Home Assistant.

## Dashboard card

The optional TeamSpeak dashboard card is included in the separate [Home Assistant Dashboard Cards](https://github.com/Hoppersusa/home-assistant-dashboard-cards) HACS Dashboard repository.

## Security

Use a dedicated, least-privilege ServerQuery account. The password is stored in the Home Assistant config entry and is never exposed through the entity state or attributes.

## License

MIT. See `LICENSE` and `NOTICE`.
