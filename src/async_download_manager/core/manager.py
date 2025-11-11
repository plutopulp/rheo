"""Download manager for coordinating concurrent file downloads.

This module provides the DownloadManager class which orchestrates multiple
download workers, manages HTTP sessions, and handles priority queues.
"""

import asyncio
import typing as t
from pathlib import Path

import aiohttp

from async_download_manager.utils.filename import generate_filename

from .exceptions import ManagerNotInitializedError, ProcessQueueError
from .logger import get_logger
from .models import FileConfig
from .worker import DownloadWorker

if t.TYPE_CHECKING:
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
        download_dir: Path = Path("."),
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
        self._tasks = []  # Future: task management
        self.download_dir = download_dir

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
        await self.start_workers()
        return self

    async def __aexit__(self, *args, **kwargs) -> None:
        """Exit the async context manager.

        Cleans up resources, particularly the HTTP client if we created it.
        """
        await self.stop_workers()
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

    async def add_to_queue(self, file_configs: t.Sequence[FileConfig]) -> None:
        """Add download tasks to the priority queue.

        Args:
            file_configs: The file configurations to add to the queue.
        """
        for file_config in file_configs:
            self._logger.info(f"Adding {file_config.url} to the queue")
            await self.queue.put((-file_config.priority, file_config))

    async def process_queue(self) -> None:
        # TODO: Instead of while True, check for a shutdown event.
        while True:
            self._logger.info(
                "Waiting for a file config to be available from the queue..."
            )
            try:
                _, file_config = await self.queue.get()
                # Generate a filename for the file. Consider moving this to the file config.
                destination_path = generate_filename(file_config.url, self.download_dir)
                self._logger.info(
                    f"Downloading {file_config.url} to {destination_path}"
                )
                await self.worker.download(file_config.url, destination_path)
                self._logger.info(f"Downloaded {file_config.url} to {destination_path}")
            except Exception as e:
                # file_config may not be defined if error getting from queue.
                url = file_config.url if file_config else "unknown"
                self._logger.exception(f"Failed to process queue for file config {url}")
                raise ProcessQueueError(
                    f"Failed to process queue for file config {url}"
                ) from e
            finally:
                self.queue.task_done()

    async def start_workers(self) -> None:
        for _ in range(self.max_workers):
            task = asyncio.create_task(self.process_queue())
            self._tasks.append(task)

    async def stop_workers(self) -> None:
        for task in self._tasks:
            # request cancellation of the task
            task.cancel()
            # Note: Could add wait for cancellation completion if needed
