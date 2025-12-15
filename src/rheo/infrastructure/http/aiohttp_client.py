"""aiohttp-based HTTP client implementation."""

import typing as t
from contextlib import AbstractAsyncContextManager
from types import TracebackType

from aiohttp import ClientResponse, ClientSession, TCPConnector

from ...domain.exceptions import ClientNotInitialisedError
from .base import BaseHttpClient
from .factories import create_secure_connector


class AiohttpClient(BaseHttpClient):
    """HTTP client wrapping aiohttp with secure SSL defaults.

    Usage patterns:
        1. Context manager (recommended): async with AiohttpClient() as client: ...
        2. Custom connector: AiohttpClient(connector=create_secure_connector(limit=50))
        3. Existing session: AiohttpClient(session=my_session)
    """

    def __init__(
        self,
        session: ClientSession | None = None,
        connector: TCPConnector | None = None,
    ) -> None:
        """Initialise the client.

        Args:
            session: Existing session to use. Client does NOT take ownership;
                caller must close it. If provided, connector is ignored.
            connector: Connector for new session. Defaults to secure SSL connector.
        """
        self._session = session
        self._connector = connector
        self._owns_session = session is None

    async def __aenter__(self) -> "AiohttpClient":
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def open(self) -> None:
        """Initialise the HTTP session. Idempotent - safe to call multiple times."""
        if self._session is not None:
            return
        connector = self._connector or create_secure_connector()
        self._session = ClientSession(connector=connector)

    async def close(self) -> None:
        """Close the session if owned by this client."""
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    @property
    def closed(self) -> bool:
        """True if the client is closed or not initialised."""
        return self._session is None or self._session.closed

    def get(
        self,
        url: str,
        **kwargs: t.Any,
    ) -> AbstractAsyncContextManager[ClientResponse]:
        """Start a GET request. Use with 'async with' to stream the response.

        Raises:
            ClientNotInitialisedError: If called before open() or context entry.
        """
        if self._session is None:
            raise ClientNotInitialisedError(
                "Client not initialised. Use 'async with' or call open()."
            )
        return self._session.get(url, **kwargs)
