"""Abstract HTTP client interface."""

import typing as t
from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from types import TracebackType

from aiohttp import ClientResponse


class BaseHttpClient(ABC):
    """Abstract HTTP client for download operations.

    Implementations handle connection lifecycle, SSL configuration, and request
    execution. Response type remains aiohttp-specific for now.
    """

    @abstractmethod
    async def __aenter__(self) -> "BaseHttpClient":
        """Enter async context and initialise client."""

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context and close client."""

    @abstractmethod
    async def open(self) -> None:
        """Initialise the client. Called by __aenter__ or manually."""

    @abstractmethod
    async def close(self) -> None:
        """Close the client and release resources."""

    @property
    @abstractmethod
    def closed(self) -> bool:
        """True if the client is closed or not initialised."""

    @abstractmethod
    def get(
        self,
        url: str,
        **kwargs: t.Any,
    ) -> AbstractAsyncContextManager[ClientResponse]:
        """Perform GET request returning streaming response context."""
