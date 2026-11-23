"""Nobby Balance UART framing, based on homed-service-custom-midea (GPL-3.0)."""

import asyncio
from dataclasses import dataclass

APPLIANCE = 0xE6
SET, GET, NOTIFY, NETWORK_QUERY = 0x02, 0x03, 0x04, 0x63
HEADER_SIZE = 10
TIMEOUT = 5
POLL_PAYLOAD = bytes((1, 1)) + bytes(28)
NETWORK_PAYLOAD = bytes((1, 1, 4, 0, 0, 0, 0, 255)) + bytes(12)
TARGETS = {
    "heating_target": (0x13, 30, 80),
    "water_target": (0x12, 35, 60),
}


class CommandUnconfirmed(Exception):
    """The boiler did not report the requested setting in time."""


def crc8(data: bytes) -> int:
    """Compute the reflected Dallas/Maxim CRC used in outgoing payloads."""
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8C if crc & 1 else 0)
    return crc


def encode_frame(version: int, kind: int, payload: bytes) -> bytes:
    body = bytes((HEADER_SIZE + len(payload) + 1, APPLIANCE))
    body += bytes(5) + bytes((version, kind)) + payload + bytes((crc8(payload),))
    return b"\xaa" + body + bytes((-sum(body) & 0xFF,))


@dataclass(frozen=True)
class BoilerState:
    power: bool
    heating: bool
    flame: bool
    mode: str | None
    water_temperature: int
    water_target: int
    heating_temperature: int
    heating_target: int
    pressure: float
    error_code: int

    @classmethod
    def decode(cls, payload: bytes) -> "BoilerState":
        return cls(
            power=bool(payload[2] & 4),
            heating=bool(payload[4] & 1),
            flame=bool(payload[2] & 8),
            mode=("idle", "heating", "hot_water", None)[(payload[2] >> 4) & 3],
            water_temperature=payload[8],
            water_target=payload[12],
            heating_temperature=payload[14],
            heating_target=payload[17],
            pressure=payload[27] / 10,
            error_code=payload[6],
        )


def command_payload(field: str, value: bool | int) -> bytes:
    if field in ("power", "heating"):
        if type(value) is not bool:
            raise ValueError("Expected a boolean setting")
        setting = 1 if value else 2
        command = (setting, 1, 0) if field == "power" else (4, 1, setting)
    else:
        register, minimum, maximum = TARGETS[field]
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(f"Expected a whole number from {minimum} to {maximum}")
        command = (4, register, value)
    return bytes(command) + bytes(27)


class BoilerClient:
    """Read and control the boiler through one serialized TCP connection."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._lock = asyncio.Lock()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._buffer = bytearray()
        self._version = 0

    def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
        self._reader = self._writer = None
        self._buffer.clear()
        self._version = 0

    async def _send(self, kind: int, payload: bytes) -> None:
        self._writer.write(encode_frame(self._version, kind, payload))
        await self._writer.drain()

    async def _read_frame(self) -> bytes:
        while True:
            start = self._buffer.find(b"\xaa")
            if start < 0:
                self._buffer.clear()
            else:
                del self._buffer[:start]
                if len(self._buffer) >= 3:
                    length = self._buffer[1]
                    if length < HEADER_SIZE or self._buffer[2] != APPLIANCE:
                        del self._buffer[0]
                        continue
                    if len(self._buffer) > length:
                        frame = bytes(self._buffer[:length + 1])
                        if sum(frame[1:]) & 0xFF:
                            del self._buffer[0]
                            continue
                        del self._buffer[:length + 1]
                        return frame

            chunk = await self._reader.read(256)
            if not chunk:
                raise ConnectionError("ESPHome bridge closed the connection")
            self._buffer.extend(chunk)

    async def _read_state(self) -> BoilerState:
        while True:
            frame = await self._read_frame()
            self._version = frame[8]
            kind = frame[9]
            if kind == NETWORK_QUERY:
                await self._send(NETWORK_QUERY, NETWORK_PAYLOAD)
            elif kind in (GET, SET, NOTIFY) and len(frame) == HEADER_SIZE + 38:
                return BoilerState.decode(frame[HEADER_SIZE:-1])

    async def read(self) -> BoilerState:
        return await self._exchange()

    async def set(self, field: str, value: bool | int) -> BoilerState:
        return await self._exchange(field, value)

    async def _exchange(
        self, field: str | None = None, value: bool | int | None = None
    ) -> BoilerState:
        async with self._lock:
            try:
                async with asyncio.timeout(TIMEOUT):
                    if self._writer is None:
                        self._reader, self._writer = await asyncio.open_connection(
                            self.host, self.port
                        )
                    if field is not None:
                        # Learn the protocol version on a fresh connection and
                        # avoid writing when the requested setting already holds.
                        await self._send(GET, POLL_PAYLOAD)
                        state = await self._read_state()
                        if getattr(state, field) == value:
                            return state
                        await self._send(SET, command_payload(field, value))

                    await self._send(GET, POLL_PAYLOAD)
                    while True:
                        state = await self._read_state()
                        if field is None or getattr(state, field) == value:
                            return state
            except TimeoutError as err:
                self.close()
                if field is not None:
                    raise CommandUnconfirmed from err
                raise
            except (OSError, asyncio.CancelledError):
                self.close()
                raise
