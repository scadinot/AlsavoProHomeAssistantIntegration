"""Asynchronous UDP client used to talk to the Alsavo Pro heat pump."""
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5.0


class UDPClient:
    """Minimal async UDP client (request/response and fire-and-forget)."""

    def __init__(self, server_host: str, server_port: int) -> None:
        self.server_host = server_host
        self.server_port = server_port

    class _EchoClientProtocol(asyncio.DatagramProtocol):
        """Send a datagram and resolve a future with the first reply."""

        def __init__(self, message: bytes, future: asyncio.Future) -> None:
            self.message = message
            self.future = future
            self.transport = None

        def connection_made(self, transport) -> None:
            self.transport = transport
            transport.sendto(self.message)

        def datagram_received(self, data: bytes, addr) -> None:
            if not self.future.done():
                self.future.set_result(data)
            self.transport.close()

        def error_received(self, exc) -> None:
            if not self.future.done():
                self.future.set_exception(exc)

        def connection_lost(self, exc) -> None:
            if not self.future.done():
                self.future.set_exception(ConnectionError("Connection lost"))

    async def send_rcv(
        self, bytes_to_send: bytes, timeout: float = DEFAULT_TIMEOUT
    ) -> tuple[bytes, bytes] | None:
        """Send a datagram and wait for a single reply.

        Returns a ``(data, b'0')`` tuple on success, or ``None`` on timeout.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: self._EchoClientProtocol(bytes_to_send, future),
            remote_addr=(self.server_host, self.server_port),
        )
        try:
            async with asyncio.timeout(timeout):
                data = await future
            return data, b'0'
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout: no response from server within %.1f s.", timeout)
            # Mark the future done before closing the transport so the
            # protocol callbacks don't set an exception nobody retrieves.
            future.cancel()
            return None
        finally:
            transport.close()

    async def send(self, bytes_to_send: bytes) -> None:
        """Send a datagram without waiting for a reply (fire-and-forget)."""
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            asyncio.DatagramProtocol,
            remote_addr=(self.server_host, self.server_port),
        )
        try:
            transport.sendto(bytes_to_send)
        finally:
            transport.close()
