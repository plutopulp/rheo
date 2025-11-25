"""Download manager for coordinating concurrent file downloads.

This module provides the DownloadManager class which orchestrates multiple
download workers, manages HTTP sessions, and handles priority queues.
"""

import asyncio
import ssl
import typing as t
from pathlib import Path

import aiofiles.os
import aiohttp
import certifi

from ..domain.exceptions import ManagerNotInitializedError
from ..domain.file_config import FileConfig
from ..infrastructure.logging import get_logger
from ..tracking.base import BaseTracker
from ..tracking.tracker import DownloadTracker
from .queue import PriorityDownloadQueue
from .worker.factory import WorkerFactory
from .worker.worker import DownloadWorker
from .worker_pool.factory import WorkerPoolFactory
from .worker_pool.pool import WorkerPool

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
            await manager.add_to_queue([file_config])
            await manager.queue.join()

    Or with custom dependencies:
        async with DownloadManager(client=custom_session) as manager:
            # Uses provided session instead of creating one
    """

    def __init__(
        self,
        client: aiohttp.ClientSession | None = None,
        worker_factory: WorkerFactory | None = None,
        queue: PriorityDownloadQueue | None = None,
        tracker: BaseTracker | None = None,
        timeout: float | None = None,
        max_concurrent: int = 3,
        logger: "loguru.Logger" = get_logger(__name__),
        download_dir: Path = Path("."),
        worker_pool_factory: WorkerPoolFactory | None = None,
    ) -> None:
        """Initialise the download manager.

        Args:
            client: HTTP session for downloads. If None, one will be created.
            worker_factory: Factory function for creating workers. If None, defaults
                           to DownloadWorker constructor.
            queue: Priority download queue for tasks. If None, one will be created.
            tracker: Download tracker for observability. If None, a DownloadTracker
                    will be created automatically. Pass NullTracker() to
                    disable tracking.
            timeout: Default timeout for downloads in seconds.
            max_concurrent: Maximum number of concurrent downloads. Defaults to 3.
            logger: Logger instance for recording manager events.
            download_dir: Directory where downloaded files will be saved.
            worker_pool_factory: Factory for creating the worker pool. If None,
                    defaults to WorkerPool constructor.
        """
        self._client = client
        self._owns_client = False  # Track if we created the client
        self._worker_factory = worker_factory or DownloadWorker
        self._logger = logger
        # Auto-create tracker if not provided (always available for observability)
        # Users can pass NullTracker() if tracking is unwanted
        self._tracker = (
            tracker if tracker is not None else DownloadTracker(logger=logger)
        )
        self.queue = queue or PriorityDownloadQueue(logger=logger)
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.download_dir = download_dir

        pool_factory = worker_pool_factory or WorkerPool
        self._worker_pool = pool_factory(
            queue=self.queue,
            worker_factory=self._worker_factory,
            tracker=self._tracker,
            logger=logger,
            download_dir=download_dir,
            max_workers=self.max_concurrent,
        )

    @property
    def tracker(self) -> BaseTracker:
        """Access the download tracker for querying download state and subscribing
        to events.

        The tracker is always available - if not explicitly provided during
        initialization, a DownloadTracker is created automatically.

        Returns:
            BaseTracker: The download tracker instance

        Example:
            ```python
            async with DownloadManager(download_dir=Path("./downloads")) as manager:
                await manager.add_to_queue([file_config])
                await manager.queue.join()

                # Query download status
                info = manager.tracker.get_download_info(str(url))
                if info and info.status == DownloadStatus.FAILED:
                    print(f"Download failed: {info.error}")
            ```
        """
        return self._tracker

    async def __aenter__(self) -> "DownloadManager":
        """Enter the async context manager.

        Initializes HTTP client and starts worker tasks.
        Each worker gets its own emitter for isolation.
        Ensures download directory exists.

        Returns:
            Self for use in async with statements.
        """
        # Ensure download directory exists (async to avoid blocking event loop)
        await aiofiles.os.makedirs(self.download_dir, exist_ok=True)

        if self._client is None:
            # Create SSL context using certifi's certificate bundle for portable
            # SSL certificate verification across all platforms and Python versions
            # e.g. SSL certs not handled by default on macOS with Python 3.14
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._client = await aiohttp.ClientSession(connector=connector).__aenter__()
            self._owns_client = True

        await self.start_workers()
        return self

    async def __aexit__(self, *args: t.Any, **kwargs: t.Any) -> None:
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
    def is_active(self) -> bool:
        """Check if the manager is active and ready to process downloads.

        Returns True when the manager has been initialised (via open() or
        context manager entry) and workers are running. Returns False before
        initialisation or after closing.

        Note: This indicates readiness to accept downloads, not necessarily
        that downloads are currently in progress.

        Returns:
            True if manager is active and can process downloads, False otherwise.

        Example:
            manager = DownloadManager(...)
            assert not manager.is_active  # Not yet opened

            await manager.open()
            assert manager.is_active      # Ready to process

            await manager.close()
            assert not manager.is_active  # Closed
        """
        return self._worker_pool.is_running

    async def add(self, files: t.Sequence[FileConfig]) -> None:
        """Add files to download queue.

        Files will be downloaded concurrently according to their priority.
        Lower priority numbers are downloaded first.

        Note: You can call this method multiple times. Workers continue
        processing new files as they're added, even after wait_until_complete()
        returns.

        Args:
            files: File configurations to download

        Example:
            await manager.add([file1, file2])
            await manager.wait_until_complete()  # Wait for batch 1
            await manager.add([file3, file4])    # Add more - workers still running
            await manager.wait_until_complete()  # Wait for batch 2
        """
        await self.queue.add(files)

    async def wait_until_complete(self, timeout: float | None = None) -> None:
        """Wait for all currently queued downloads to complete.

        Blocks until the download queue is empty. Workers remain active after
        this returns, so you can add more files and call this again.

        Args:
            timeout: Optional timeout in seconds. If None, waits indefinitely.

        Raises:
            asyncio.TimeoutError: If timeout is exceeded

        Example:
            # Single batch
            await manager.add([file1, file2, file3])
            await manager.wait_until_complete()

            # Multiple batches
            await manager.add([file1, file2])
            await manager.wait_until_complete(timeout=60)
            await manager.add([file3])
            await manager.wait_until_complete()
        """
        if timeout:
            await asyncio.wait_for(self.queue.join(), timeout=timeout)
        else:
            await self.queue.join()

    async def cancel_all(self, wait_for_current: bool = False) -> None:
        """Cancel all pending downloads and stop workers.

        Stops accepting new downloads and cancels pending items in the queue.
        After calling this, you cannot add more files without restarting the
        manager (exit and re-enter context manager, or call close() then open()).

        Args:
            wait_for_current: If True, waits for currently downloading files
                            to finish before cancelling pending items.
                            If False, cancels everything immediately including
                            in-progress downloads.

        Example:
            # Graceful cancellation
            await manager.cancel_all(wait_for_current=True)

            # Immediate cancellation
            await manager.cancel_all(wait_for_current=False)
        """
        await self._worker_pool.shutdown(wait_for_current=wait_for_current)

    async def open(self) -> None:
        """Manually initialize the manager.

        Use this if you need manual control over the manager lifecycle
        instead of using it as a context manager. You must call close()
        when done to clean up resources.

        This method:
        - Creates the download directory if it doesn't exist
        - Creates an HTTP client session (if not provided)
        - Starts worker tasks to process downloads

        Example:
            manager = DownloadManager(...)
            await manager.open()
            try:
                await manager.add([file1, file2])
                await manager.wait_until_complete()
            finally:
                await manager.close()
        """
        # Ensure download directory exists
        await aiofiles.os.makedirs(self.download_dir, exist_ok=True)

        if self._client is None:
            # Create SSL context using certifi's certificate bundle
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._client = await aiohttp.ClientSession(connector=connector).__aenter__()
            self._owns_client = True

        await self.start_workers()

    async def close(self, wait_for_current: bool = False) -> None:
        """Manually clean up manager resources.

        Use this to close a manager that was opened with open().
        This method is idempotent - calling it multiple times is safe.

        Args:
            wait_for_current: If True, waits for currently downloading files
                            to finish before stopping. If False, stops
                            immediately.

        Example:
            manager = DownloadManager(...)
            await manager.open()
            try:
                await manager.add([file1, file2])
                await manager.wait_until_complete()
            finally:
                await manager.close(wait_for_current=True)
        """
        if wait_for_current:
            await self._worker_pool.shutdown(wait_for_current=True)
        else:
            await self.stop_workers()

        if self._owns_client and self._client is not None:
            await self._client.close()

    async def add_to_queue(self, file_configs: t.Sequence[FileConfig]) -> None:
        """Add download tasks to the priority queue.

        Args:
            file_configs: The file configurations to add to the queue.
        """
        await self.queue.add(file_configs)

    async def shutdown(self, wait_for_current: bool = True) -> None:
        """Initiate graceful shutdown of all workers.

        Args:
            wait_for_current: If True, wait for current downloads to complete.
                            If False, cancel immediately via stop_workers().
        """
        self._logger.debug(f"Initiating shutdown (wait_for_current={wait_for_current})")
        await self._worker_pool.shutdown(wait_for_current=wait_for_current)

    def request_shutdown(self) -> None:
        """Signal workers to stop accepting new work.

        This is the non-blocking equivalent of initiating shutdown.
        Workers will finish current tasks (if running) and then exit.
        """
        self._worker_pool.request_shutdown()

    async def start_workers(self) -> None:
        """Start worker tasks that process the download queue.

        Delegates to the worker pool to create and manage worker tasks.
        """
        await self._worker_pool.start(self.client)

    async def stop_workers(self) -> None:
        """Stop all worker tasks and wait for them to complete.

        Delegates to the worker pool to stop all workers immediately.
        """
        await self._worker_pool.stop()
