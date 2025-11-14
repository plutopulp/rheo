"""Download manager for coordinating concurrent file downloads.

This module provides the DownloadManager class which orchestrates multiple
download workers, manages HTTP sessions, and handles priority queues.
"""

import asyncio
import typing as t
from pathlib import Path

import aiohttp

from ..domain.exceptions import ManagerNotInitializedError
from ..domain.file_config import FileConfig
from ..events import (
    WorkerEvent,
)
from ..infrastructure.logging import get_logger
from ..tracking.base import BaseTracker
from .queue import PriorityDownloadQueue
from .worker import DownloadWorker

if t.TYPE_CHECKING:
    import loguru


def _create_event_wiring(
    tracker: BaseTracker,
    # TODO: type this properly
) -> dict[str, t.Any]:
    """Create event wiring mapping from worker events to tracker methods.

    Returns dict mapping event types to async handler functions.
    """
    return {
        "worker.started": lambda e: tracker.track_started(e.url, e.total_bytes),
        "worker.progress": lambda e: tracker.track_progress(
            e.url, e.bytes_downloaded, e.total_bytes
        ),
        "worker.completed": lambda e: tracker.track_completed(
            e.url, e.total_bytes, e.destination_path
        ),
        "worker.failed": lambda e: tracker.track_failed(
            e.url, Exception(f"{e.error_type}: {e.error_message}")
        ),
    }


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
        queue: PriorityDownloadQueue | None = None,
        tracker: BaseTracker | None = None,
        timeout: float | None = None,
        max_workers: int = 3,
        logger: "loguru.Logger" = get_logger(__name__),
        download_dir: Path = Path("."),
    ) -> None:
        """Initialize the download manager.

        Args:
            client: HTTP session for downloads. If None, one will be created.
            worker: Download worker instance. If None, one will be created.
            queue: Priority download queue for tasks. If None, one will be created.
            tracker: Download tracker for observability. Optional - if None, no tracking.
            timeout: Default timeout for downloads in seconds.
            max_workers: Maximum number of concurrent workers.
            logger: Logger instance for recording manager events.
            download_dir: Directory where downloaded files will be saved.
        """
        self._client = client
        self._owns_client = False  # Track if we created the client
        self._worker = worker
        self._logger = logger
        self._tracker = tracker
        self.queue = queue or PriorityDownloadQueue(logger=logger)
        self.timeout = timeout
        self.max_workers = max_workers
        self._tasks: list[asyncio.Task[None]] = []
        self._shutdown_event = asyncio.Event()
        self.download_dir = download_dir

    def _wire_worker_events(
        self,
        event_wiring: (
            dict[str, t.Callable[[WorkerEvent], t.Awaitable[None]]] | None
        ) = None,
    ) -> None:
        """Wire worker events to tracker using provided or default mapping.

        Args:
            event_wiring: Custom event wiring dict. If None, uses default wiring.

        Note: Future improvement - store handler references for cleanup in __aexit__().
        """
        if self._worker is None or self._tracker is None:
            return

        wiring = event_wiring or _create_event_wiring(self._tracker)

        for event_type, handler in wiring.items():
            # Register async handler with worker emitter
            self._worker.emitter.on(event_type, handler)

    async def __aenter__(self) -> "DownloadManager":
        """Enter the async context manager.

        Initializes HTTP client and worker if not provided during construction.
        Wires worker events to tracker if both are available.

        Returns:
            Self for use in async with statements.
        """
        if self._client is None:
            self._client = await aiohttp.ClientSession().__aenter__()
            self._owns_client = True
        if self._worker is None:
            self._worker = DownloadWorker(self._client, self._logger)

        # Wire worker events to tracker
        self._wire_worker_events()

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
        await self.queue.add(file_configs)

    async def shutdown(self, wait_for_current: bool = True) -> None:
        """Initiate graceful shutdown of all workers.

        Args:
            wait_for_current: If True, wait for current downloads to complete.
                            If False, cancel immediately via stop_workers().
        """
        self._logger.info(f"Initiating shutdown (wait_for_current={wait_for_current})")
        self._shutdown_event.set()

        if wait_for_current:
            # Wait for workers to finish current downloads
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
        else:
            # Cancel immediately
            await self.stop_workers()

    async def process_queue(self) -> None:
        """Process downloads from queue until shutdown or cancellation.

        Uses event-based shutdown mechanism to allow graceful termination.
        Workers periodically check the shutdown event and can complete current
        downloads before exiting.
        """
        while not self._shutdown_event.is_set():
            file_config = None
            got_item = False
            try:
                # Use timeout to prevent indefinite blocking on empty queue.
                # Without timeout, worker would be stuck waiting and couldn't
                # respond to shutdown until a new item arrives. The 1-second
                # timeout allows checking shutdown event every second maximum.
                # Note that this does not impact when a worker starts a download, but
                # sets the maximum time a worker can be blocked waiting for an item.
                file_config = await asyncio.wait_for(self.queue.get_next(), timeout=1.0)
                got_item = True

                # Check shutdown again before starting download
                if self._shutdown_event.is_set():
                    # Put item back in queue if shutting down, then call task_done()
                    # to balance the accounting. The get() incremented the unfinished
                    # task counter, so we must decrement it even though we're re-queuing.
                    # Without task_done(), queue.join() would hang waiting for this item.
                    # (asyncio.PriorityQueue._unfinished)
                    await self.queue.add([file_config])
                    self.queue.task_done()
                    break

                # FileConfig generates destination path and creates directories if needed
                destination_path = file_config.get_destination_path(self.download_dir)

                self._logger.info(
                    f"Downloading {file_config.url} to {destination_path}"
                )
                await self.worker.download(str(file_config.url), destination_path)
                self._logger.info(f"Downloaded {file_config.url} to {destination_path}")
            except asyncio.TimeoutError:
                # No item available within timeout period. This is normal when
                # queue is empty or all items were taken by other workers.
                # Loop continues to check shutdown event and retry.
                continue
            except asyncio.CancelledError:
                # Raised when task.cancel() is called (immediate shutdown).
                # Must re-raise to properly terminate the task, otherwise
                # asyncio considers cancellation "handled" and keeps running.
                self._logger.info("Worker cancelled, stopping immediately")
                raise
            except Exception as e:
                # file_config may not be defined if error getting from queue.
                url = file_config.url if file_config else "unknown"
                self._logger.error(f"Failed to download {url}: {type(e).__name__}: {e}")
                # Continue processing other items instead of crashing
                # Error details are already logged by the worker
            finally:
                # Only call task_done if we actually got an item
                if got_item:
                    self.queue.task_done()

        self._logger.info("Worker shutting down gracefully")

    async def start_workers(self) -> None:
        for _ in range(self.max_workers):
            task = asyncio.create_task(self.process_queue())
            self._tasks.append(task)

    async def stop_workers(self) -> None:
        """Stop all worker tasks and wait for them to complete.

        Requests cancellation of all worker tasks and waits for them to finish
        before returning. This ensures proper cleanup before closing resources.
        """
        for task in self._tasks:
            task.cancel()

        # Wait for all tasks to complete (including handling CancelledError)
        await asyncio.gather(*self._tasks, return_exceptions=True)

        # Clear the tasks list
        self._tasks.clear()
