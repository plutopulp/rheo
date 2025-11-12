"""Download manager for coordinating concurrent file downloads.

This module provides the DownloadManager class which orchestrates multiple
download workers, manages HTTP sessions, and handles priority queues.
"""

import asyncio
import typing as t
from pathlib import Path

import aiohttp

from async_download_manager.utils.filename import generate_filename

from ..domain.downloads import FileConfig
from ..domain.exceptions import ManagerNotInitializedError, ProcessQueueError
from ..events import WorkerEvent
from ..infrastructure.logging import get_logger
from ..tracking.base import BaseTracker
from .queue import PriorityDownloadQueue
from .worker import DownloadWorker

if t.TYPE_CHECKING:
    import loguru


def _create_event_wiring(
    tracker: BaseTracker,
) -> dict[str, t.Callable[[WorkerEvent], t.Awaitable[None]]]:
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
        self.queue = queue or PriorityDownloadQueue(logger)
        self.timeout = timeout
        self.max_workers = max_workers
        self._tasks = []  # Future: task management
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
        await self.queue.add(file_configs)

    async def process_queue(self) -> None:
        # TODO: Instead of while True, check for a shutdown event.
        while True:
            file_config = None
            got_item = False
            try:
                file_config = await self.queue.get_next()
                got_item = True
                # Generate a filename for the file.
                # Consider moving this to the file config.
                filename = generate_filename(file_config.url)
                destination_path = self.download_dir / filename
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
                # Only call task_done if we actually got an item
                if got_item:
                    self.queue.task_done()

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
