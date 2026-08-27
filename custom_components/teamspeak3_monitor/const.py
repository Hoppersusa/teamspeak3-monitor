"""Constants for the TeamSpeak 3 Monitor integration."""

from homeassistant.const import Platform

DOMAIN = "teamspeak3_monitor"
PLATFORMS = [Platform.SENSOR]

CONF_QUERY_PORT = "query_port"
CONF_USERNAME = "username"
CONF_VOICE_PORT = "voice_port"
CONF_SERVER_ID = "server_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_QUERY_PORT = 10011
DEFAULT_VOICE_PORT = 9987
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_TIMEOUT = 10
MIN_SCAN_INTERVAL = 5
