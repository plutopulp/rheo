"""Download manager for coordinating concurrent file downloads.

This module provides the DownloadManager class which orchestrates multiple
download workers, manages HTTP sessions, and handles priority queues.
"""

import asyncio
from typing import TYPE_CHECKING

import aiohttp

from .exceptions import ManagerNotInitializedError
from .logger import get_logger
from .models import FileConfig
from .worker import DownloadWorker

if TYPE_CHECKING:
    import loguru


class DownloadManager:
    """Manages concurrent downloads with priority queuing and resource coordination.

    The DownloadManager serves as the orchestration layer, coordinating workers,
    HTTP sessions, and download queues. It uses the context manager pattern for
    automatic resource management.

    Key responsibilities:
    - HTTP session lifecycle management
    - Worker coordination and resource allocation
    - Priority queue management
    - Automatic cleanup on exit

    Usage:
        async with DownloadManager() as manager:
            # manager.client and manager.worker are now available
            await manager.worker.download(url, path)

    Or with custom dependencies:
        async with DownloadManager(client=custom_session) as manager:
            # Uses provided session instead of creating one
    """

    def __init__(
        self,
        client: aiohttp.ClientSession | None = None,
        worker: DownloadWorker | None = None,
        queue: asyncio.PriorityQueue[tuple[int, FileConfig]] | None = None,
        timeout: float | None = None,
        max_workers: int = 3,
        logger: "loguru.Logger" = get_logger(__name__),
    ) -> None:
        """Initialize the download manager.

        Args:
            client: HTTP session for downloads. If None, one will be created.
            worker: Download worker instance. If None, one will be created.
            queue: Priority queue for download tasks. If None, one will be created.
            timeout: Default timeout for downloads in seconds.
            max_workers: Maximum number of concurrent workers.
            logger: Logger instance for recording manager events.
        """
        self._client = client
        self._owns_client = False  # Track if we created the client
        self._worker = worker
        self._logger = logger
        self.queue = queue or asyncio.PriorityQueue()
        self.timeout = timeout
        self.max_workers = max_workers
        self.workers = []  # Future: active worker tracking
        self._tasks = []  # Future: task management

    async def __aenter__(self) -> "DownloadManager":
        """Enter the async context manager.

        Initializes HTTP client and worker if not provided during construction.
        This ensures all dependencies are available before use.

        Returns:
            Self for use in async with statements.
        """
        if self._client is None:
            self._client = await aiohttp.ClientSession().__aenter__()
            self._owns_client = True
        if self._worker is None:
            self._worker = DownloadWorker(self._client, self._logger)
        return self

    async def __aexit__(self, *args, **kwargs) -> None:
        """Exit the async context manager.

        Cleans up resources, particularly the HTTP client if we created it.
        """
        if self._owns_client and self._client is not None:
            await self._client.__aexit__(*args, **kwargs)

    @property
    def client(self) -> aiohttp.ClientSession:
        """Get the HTTP client session.

        Returns:
            The aiohttp ClientSession for making HTTP requests.

        Raises:
            ManagerNotInitializedError: If accessed before entering context manager
                or without providing a client during initialization.
        """
        if self._client is None:
            raise ManagerNotInitializedError(
                (
                    "DownloadManager must be used as a context manager or "
                    "initialized with a client"
                )
            )
        return self._client

    @property
    def worker(self) -> DownloadWorker:
        """Get the download worker instance.

        Returns:
            The DownloadWorker instance for performing downloads.

        Raises:
            ManagerNotInitializedError: If accessed before entering context manager
                or without providing a worker during initialization.
        """
        if self._worker is None:
            raise ManagerNotInitializedError(
                (
                    "DownloadManager must be used as a context manager or "
                    "initialized with a worker"
                )
            )
        return self._worker
