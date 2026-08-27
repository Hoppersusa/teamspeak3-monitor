"""Minimal asynchronous TeamSpeak 3 ServerQuery client."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass


class TeamSpeakError(Exception):
    """Base exception for TeamSpeak ServerQuery errors."""


class TeamSpeakConnectionError(TeamSpeakError):
    """Raised when the ServerQuery connection closes unexpectedly."""


class TeamSpeakAuthenticationError(TeamSpeakError):
    """Raised when ServerQuery rejects the configured credentials."""


class TeamSpeakResponseError(TeamSpeakError):
    """Raised when ServerQuery returns an unsuccessful response."""

    def __init__(self, error_id: int, message: str) -> None:
        super().__init__(f"TeamSpeak ServerQuery error {error_id}: {message}")
        self.error_id = error_id
        self.message = message


@dataclass(frozen=True, slots=True)
class TeamSpeakClient:
    """A connected non-ServerQuery TeamSpeak client."""

    nickname: str
    client_id: int | None = None
    channel_id: int | None = None


_ESCAPE = {
    "\\": "\\\\",
    "/": "\\/",
    " ": "\\s",
    "|": "\\p",
    "\a": "\\a",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\v": "\\v",
}

_UNESCAPE = {
    "\\": "\\",
    "/": "/",
    "s": " ",
    "p": "|",
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
}


def escape_query_value(value: str) -> str:
    """Escape a value for the TeamSpeak ServerQuery protocol."""
    return "".join(_ESCAPE.get(character, character) for character in str(value))


def unescape_query_value(value: str) -> str:
    """Unescape a TeamSpeak ServerQuery value."""
    output: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character == "\\" and index + 1 < len(value):
            code = value[index + 1]
            output.append(_UNESCAPE.get(code, code))
            index += 2
            continue
        output.append(character)
        index += 1
    return "".join(output)


def parse_query_records(lines: list[str]) -> list[dict[str, str]]:
    """Parse one or more ServerQuery data lines into record dictionaries."""
    records: list[dict[str, str]] = []
    for line in lines:
        for raw_record in line.split("|"):
            fields: dict[str, str] = {}
            for token in raw_record.split(" "):
                if not token:
                    continue
                key, separator, value = token.partition("=")
                fields[key] = unescape_query_value(value) if separator else ""
            if fields:
                records.append(fields)
    return records


class TeamSpeakQueryClient:
    """Query online clients from a TeamSpeak 3 server."""

    def __init__(
        self,
        host: str,
        query_port: int,
        username: str,
        password: str,
        *,
        voice_port: int = 9987,
        server_id: int | None = None,
        timeout: float = 10,
    ) -> None:
        self.host = host
        self.query_port = query_port
        self.username = username
        self.password = password
        self.voice_port = voice_port
        self.server_id = server_id
        self.timeout = timeout

    async def async_get_clients(self) -> tuple[TeamSpeakClient, ...]:
        """Connect, authenticate, select a virtual server, and list clients."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.query_port),
                timeout=self.timeout,
            )
        except (OSError, asyncio.TimeoutError) as error:
            raise TeamSpeakConnectionError(str(error)) from error

        try:
            await self._read_greeting(reader)
            username = escape_query_value(self.username)
            password = escape_query_value(self.password)
            await self._command(
                reader,
                writer,
                f"login client_login_name={username} client_login_password={password}",
                authentication=True,
            )

            selector = (
                f"sid={self.server_id}"
                if self.server_id is not None
                else f"port={self.voice_port}"
            )
            await self._command(reader, writer, f"use {selector}")
            lines = await self._command(reader, writer, "clientlist")
            records = parse_query_records(lines)

            clients: list[TeamSpeakClient] = []
            for record in records:
                if record.get("client_type") != "0":
                    continue
                nickname = record.get("client_nickname", "").strip()
                if not nickname:
                    continue
                clients.append(
                    TeamSpeakClient(
                        nickname=nickname,
                        client_id=self._optional_int(record.get("clid")),
                        channel_id=self._optional_int(record.get("cid")),
                    )
                )
            return tuple(clients)
        finally:
            if not writer.is_closing():
                writer.write(b"quit\n")
                with suppress(OSError, ConnectionError, asyncio.TimeoutError):
                    await asyncio.wait_for(writer.drain(), timeout=1)
            writer.close()
            with suppress(OSError, ConnectionError, asyncio.TimeoutError):
                await asyncio.wait_for(writer.wait_closed(), timeout=1)

    async def _read_greeting(self, reader: asyncio.StreamReader) -> None:
        """Consume the ServerQuery greeting."""
        greeting: list[str] = []
        for _ in range(8):
            line = await self._readline(reader)
            if not line:
                if greeting:
                    break
                continue
            greeting.append(line)
            if len(greeting) >= 2 and line.startswith("Welcome"):
                # A blank line normally follows; consuming it is optional because
                # _command safely ignores blank response lines.
                break
        if not any(line == "TS3" for line in greeting):
            raise TeamSpeakConnectionError("The endpoint did not return a TeamSpeak ServerQuery greeting")

    async def _command(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        command: str,
        *,
        authentication: bool = False,
    ) -> list[str]:
        """Send one command and read through its final error response."""
        writer.write(f"{command}\n".encode("utf-8"))
        try:
            await asyncio.wait_for(writer.drain(), timeout=self.timeout)
        except (OSError, ConnectionError, asyncio.TimeoutError) as error:
            raise TeamSpeakConnectionError(str(error)) from error

        data: list[str] = []
        while True:
            line = await self._readline(reader)
            if not line:
                continue
            if not line.startswith("error "):
                data.append(line)
                continue

            fields = parse_query_records([line])[0]
            error_id = self._optional_int(fields.get("id")) or 0
            message = fields.get("msg", "Unknown ServerQuery error")
            if error_id != 0:
                if authentication:
                    raise TeamSpeakAuthenticationError(message)
                raise TeamSpeakResponseError(error_id, message)
            return data

    async def _readline(self, reader: asyncio.StreamReader) -> str:
        """Read a decoded protocol line or fail on an unexpected close."""
        try:
            raw_line = await asyncio.wait_for(reader.readline(), timeout=self.timeout)
        except (OSError, ConnectionError, asyncio.TimeoutError) as error:
            raise TeamSpeakConnectionError(str(error)) from error
        if not raw_line:
            raise TeamSpeakConnectionError("The ServerQuery connection closed unexpectedly")
        return raw_line.decode("utf-8", errors="replace").strip("\r\n")

    @staticmethod
    def _optional_int(value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
