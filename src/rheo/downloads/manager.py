"""Download manager for coordinating concurrent file downloads.

This module provides the DownloadManager class which orchestrates multiple
download workers, manages HTTP sessions, and handles priority queues.
"""

import asyncio
import typing as t
from pathlib import Path
from types import TracebackType

import aiofiles.os

from ..domain.cancellation import CancelResult
from ..domain.downloads import DownloadInfo, DownloadStats
from ..domain.exceptions import ManagerNotInitialisedError, PendingDownloadsError
from ..domain.file_config import FileConfig, FileExistsStrategy
from ..events import EventEmitter, Subscription
from ..events.base import BaseEmitter
from ..events.models.download import EventHandler, EventType
from ..infrastructure.http import AiohttpClient, BaseHttpClient
from ..infrastructure.logging import get_logger
from ..tracking.base import BaseTracker
from ..tracking.tracker import DownloadTracker
from .queue import PriorityDownloadQueue
from .retry.base import BaseRetryHandler
from .retry.null import NullRetryHandler
from .worker.factory import WorkerFactory
from .worker.worker import DownloadWorker
from .worker_pool.factory import WorkerPoolFactory
from .worker_pool.pool import EventSource, EventWiring, WorkerPool

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

    Basic Usage:
        async with DownloadManager() as manager:
            await manager.add([file_config])
            await manager.wait_until_complete()

    With Configuration:
        async with DownloadManager(
            max_concurrent=5,
            download_dir=Path("./downloads")
        ) as manager:
            await manager.add(files)
            await manager.wait_until_complete()

    Manual Lifecycle (without context manager):
        manager = DownloadManager()
        await manager.open()
        try:
            await manager.add(files)
            await manager.wait_until_complete()
        finally:
            await manager.close()

    Closing with Options:
        async with DownloadManager() as manager:
            await manager.add(files)
            # Close immediately (cancels in-progress downloads)
            await manager.close()

            # Or wait for current downloads to finish first
            await manager.close(wait_for_current=True)
    """

    def __init__(
        self,
        client: BaseHttpClient | None = None,
        worker_factory: WorkerFactory | None = None,
        queue: PriorityDownloadQueue | None = None,
        tracker: BaseTracker | None = None,
        timeout: float | None = None,
        max_concurrent: int = 3,
        logger: "loguru.Logger" = get_logger(__name__),
        download_dir: Path = Path("."),
        worker_pool_factory: WorkerPoolFactory | None = None,
        file_exists_strategy: FileExistsStrategy = FileExistsStrategy.SKIP,
        event_wiring: EventWiring | None = None,
        emitter: BaseEmitter | None = None,
        retry_handler: BaseRetryHandler | None = None,
    ) -> None:
        """Initialise the download manager.

        Args:
            client: HTTP client for downloads. If None, one will be created.
            worker_factory: Factory function for creating workers. If None, defaults
                           to DownloadWorker constructor.
            queue: Priority download queue for tasks. If None, one will be created.
                  To customise queue events, create a queue with your own emitter.
            tracker: Download tracker for observability. If None, a DownloadTracker
                    will be created automatically. Pass NullTracker() to
                    disable tracking.
            timeout: Default timeout for downloads in seconds.
            max_concurrent: Maximum number of concurrent downloads. Defaults to 3.
            logger: Logger instance for recording manager events.
            download_dir: Directory where downloaded files will be saved.
            worker_pool_factory: Factory for creating the worker pool. If None,
                    defaults to WorkerPool constructor.
            file_exists_strategy: Default strategy for handling existing files.
                    Defaults to SKIP.
            event_wiring: Optional wiring map for download events to tracker handlers.
                    If None, defaults to internal wiring.
            emitter: Shared event emitter for queue, workers, and external subscribers.
                    If None, a new EventEmitter will be created.
            retry_handler: Retry handler for automatic retries on transient errors.
                    If None, NullRetryHandler is used (no retries).
        """
        self._client = client
        self._owns_client = False  # Track if we created the client
        self._worker_factory = worker_factory or DownloadWorker
        self._logger = logger
        self._emitter = emitter or EventEmitter(logger)
        self._retry_handler = retry_handler or NullRetryHandler()
        # TODO: Reconsider this pattern - mutating injected dependency is a code smell.
        # Consider alternative: accept RetryConfig and construct handler internally,
        # or define a protocol for handlers that need emitter injection.
        if hasattr(self._retry_handler, "emitter"):
            self._retry_handler.emitter = self._emitter
        # Auto-create tracker if not provided (always available for observability)
        # Users can pass NullTracker() if tracking is unwanted
        self._tracker = (
            tracker if tracker is not None else DownloadTracker(logger=logger)
        )

        # Create queue with shared emitter for automatic tracking.
        # Pool wires queue.emitter to tracker automatically.
        # To disable queue events, pass a queue with NullEmitter.
        self.queue = queue or PriorityDownloadQueue(
            logger=logger, emitter=self._emitter
        )
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.download_dir = download_dir
        self.file_exists_strategy = file_exists_strategy
        self._event_wiring = event_wiring or self._create_event_wiring()

        pool_factory = worker_pool_factory or WorkerPool
        self._worker_pool = pool_factory(
            queue=self.queue,
            worker_factory=self._worker_factory,
            logger=logger,
            download_dir=download_dir,
            max_workers=self.max_concurrent,
            event_wiring=self._event_wiring,
            file_exists_strategy=self.file_exists_strategy,
            emitter=self._emitter,
            retry_handler=self._retry_handler,
        )

    @property
    def tracker(self) -> BaseTracker:
        """Access the download tracker for querying download state and subscribing
        to events.

        The tracker is always available - if not explicitly provided during
        initialisation, a DownloadTracker is created automatically.

        Returns:
            BaseTracker: The download tracker instance

        Example:
            ```python
            async with DownloadManager(download_dir=Path("./downloads")) as manager:
                await manager.add([file_config])
                await manager.wait_until_complete()

                # Query download status
                info = manager.tracker.get_download_info(str(url))
                if info and info.status == DownloadStatus.FAILED:
                    print(f"Download failed: {info.error}")
            ```
        """
        return self._tracker

    def get_download_info(self, download_id: str) -> DownloadInfo | None:
        """Get current state of a download.

        Args:
            download_id: The download ID to query (generated during FileConfig creation)

        Returns:
            DownloadInfo if found, None otherwise

        Example:
            info = manager.get_download_info("https://example.com/file.zip")
            if info and info.status == DownloadStatus.COMPLETED:
                print(f"Downloaded to: {info.destination_path}")
        """
        return self._tracker.get_download_info(download_id)

    @property
    def stats(self) -> DownloadStats:
        """Get aggregate download statistics.

        Returns:
            DownloadStats with counts by status and total bytes

        Example:
            stats = manager.stats
            print(f"Completed: {stats.completed}/{stats.total}")
        """
        return self._tracker.get_stats()

    def on(self, event_type: EventType, handler: EventHandler) -> Subscription:
        """Subscribe to download events.

        Args:
            event_type: Event to subscribe to. Use DownloadEventType enum for
                autocomplete (e.g., DownloadEventType.COMPLETED), or "*" for
                all events.
            handler: Callback receiving the event (sync or async). Type-hint
                your handler parameter for autocomplete on event fields.

        Returns:
            Subscription handle. Call .unsubscribe() to stop receiving events.

        Example:
            def on_completed(event: DownloadCompletedEvent) -> None:
                print(f"Downloaded: {event.destination_path}")

            sub = manager.on(DownloadEventType.COMPLETED, on_completed)
            # later: sub.unsubscribe()
        """
        self._emitter.on(event_type, handler)
        return Subscription(self._emitter, event_type, handler)

    async def __aenter__(self) -> "DownloadManager":
        """Enter the async context manager.

        Initializes HTTP client and starts worker tasks.
        Each worker gets its own emitter for isolation.
        Ensures download directory exists.

        Returns:
            Self for use in async with statements.
        """
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager.

        Validates that downloads were handled before exiting. Raises
        PendingDownloadsError if there are pending downloads and we're
        not already handling an exception. Resources are always cleaned up.
        """
        # Capture state before close() changes it
        pending = self.queue.pending_count
        # If pool is still running, user didn't call close() or wait_until_complete().
        # We check this to allow explicit close(wait_for_current=True) for graceful
        # shutdown (letting in-progress downloads finish before stopping).
        # Note that this is a bit implicit and could have used a flag to track this.
        was_still_running = self._worker_pool.is_running

        # Always clean up resources
        await self.close(wait_for_current=False)

        # Raise if pool was active with pending work and not masking existing exception
        if exc_type is None and pending > 0 and was_still_running:
            raise PendingDownloadsError(pending_count=pending)

    @property
    def client(self) -> BaseHttpClient:
        """Get the HTTP client.

        Returns:
            The HTTP client for making requests.

        Raises:
            ManagerNotInitialisedError: If accessed before entering context manager
                or without providing a client during initialisation.
        """
        if self._client is None:
            raise ManagerNotInitialisedError(
                (
                    "DownloadManager must be used as a context manager or "
                    "initialised with a client"
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

    async def cancel(self, download_id: str) -> CancelResult:
        """Cancel a specific download by ID.

        Cancels both in-progress and queued downloads. Workers continue
        processing remaining queue items after cancellation.

        Args:
            download_id: The ID of the download to cancel (from FileConfig.id)

        Returns:
            CancelResult indicating what happened:
            - CANCELLED: Download was found and cancelled
            - NOT_FOUND: Download ID was never queued
            - ALREADY_TERMINAL: Download already completed/failed/skipped/cancelled

        Example:
            result = await manager.cancel(file_config.id)
            if result == CancelResult.CANCELLED:
                print("Download stopped")
        """
        # Try to cancel via pool (handles active and queued)
        if await self._worker_pool.cancel(download_id):
            return CancelResult.CANCELLED

        # Not active or queued - check if it's in a terminal state
        info = self._tracker.get_download_info(download_id)
        if info is not None and info.status.is_terminal:
            return CancelResult.ALREADY_TERMINAL

        return CancelResult.NOT_FOUND

    async def open(self) -> None:
        """Manually initialise the manager.

        Use this if you need manual control over the manager lifecycle
        instead of using it as a context manager. You must call close()
        when done to clean up resources.

        This method:
        - Creates the download directory if it doesn't exist
        - Creates an HTTP client (if not provided)
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
            self._client = AiohttpClient()
            self._owns_client = True
            await self._client.open()

        await self._worker_pool.start(self.client)

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
        await self._worker_pool.shutdown(wait_for_current=wait_for_current)

        if self._owns_client and self._client is not None:
            await self._client.close()
            self._client = None

    def _create_event_wiring(self) -> EventWiring:
        """Create event wiring for queue and worker events to tracker handlers."""
        return {
            EventSource.QUEUE: {
                "download.queued": lambda e: self._tracker._track_queued(
                    e.download_id, e.url, e.priority
                ),
            },
            EventSource.WORKER: {
                "download.started": lambda e: self._tracker._track_started(
                    e.download_id, e.url, e.total_bytes
                ),
                "download.progress": lambda e: self._tracker._track_progress(
                    e.download_id, e.url, e.bytes_downloaded, e.total_bytes, e.speed
                ),
                "download.completed": lambda e: self._tracker._track_completed(
                    e.download_id,
                    e.url,
                    e.total_bytes,
                    e.destination_path,
                    e.validation,
                ),
                "download.failed": lambda e: self._tracker._track_failed(
                    e.download_id,
                    e.url,
                    Exception(f"{e.error.exc_type}: {e.error.message}"),
                    e.validation,
                ),
                "download.skipped": lambda e: self._tracker._track_skipped(
                    e.download_id, e.url, e.reason, e.destination_path
                ),
                "download.cancelled": lambda e: self._tracker._track_cancelled(
                    e.download_id, e.url
                ),
            },
        }
