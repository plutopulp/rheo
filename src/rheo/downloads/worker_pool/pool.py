"""Concrete worker pool implementation managing worker lifecycle."""

import asyncio
import typing as t
from enum import StrEnum
from pathlib import Path

from ...domain.cancellation import CancelledFrom
from ...domain.exceptions import WorkerPoolAlreadyStartedError
from ...domain.file_config import FileConfig, FileExistsStrategy
from ...events import DownloadCancelledEvent, EventEmitter
from ...events.base import BaseEmitter
from ...infrastructure.http import BaseHttpClient
from ..queue import PriorityDownloadQueue
from ..retry.base import BaseRetryHandler
from ..retry.null import NullRetryHandler
from ..worker.base import BaseWorker
from ..worker.factory import WorkerFactory
from ..worker.worker import DownloadWorker
from .base import BaseWorkerPool

if t.TYPE_CHECKING:
    from loguru import Logger


class EventSource(StrEnum):
    """Event source categories for wiring."""

    QUEUE = "queue"
    WORKER = "worker"


# Type aliases for event wiring
EventHandler = t.Callable[[t.Any], t.Awaitable[None] | None]
EventWiring = dict[EventSource, dict[str, EventHandler]]


class WorkerPool(BaseWorkerPool):
    """Manages worker task lifecycle, queue consumption, and graceful shutdown.

    This pool encapsulates worker creation, event wiring, queue processing with
    timeout-based polling, and shutdown coordination. It handles both graceful
    shutdown (allowing in-flight downloads to complete) and immediate
    cancellation.

    Key responsibilities:
    - Creates one worker instance per task for isolation
    - Wires each EventSource emitter (queue and/or worker) to provided event handlers
    - Processes queue items with timeout to remain responsive to shutdown
    - Re-queues unstarted downloads when shutdown is requested
    - Maintains task lifecycle and cleanup

    Implementation decisions:
    - Each worker gets its own EventEmitter to prevent event cross-contamination
    - Queue polling uses 1-second timeout so workers can check shutdown event
      periodically without blocking indefinitely on empty queue
    - Shutdown check before download prevents race condition where shutdown
      triggers after queue.get() but before worker.download() starts
    - task_done() is called even when re-queuing to keep queue accounting balanced

    Usage:
        pool = WorkerPool(
            queue=queue,
            worker_factory=DownloadWorker,
            tracker=tracker,
            logger=logger,
            download_dir=Path("./downloads"),
            max_workers=3,
        )

        await pool.start(client)
        # Workers now processing queue
        await pool.shutdown(wait_for_current=True)
    """

    def __init__(
        self,
        queue: PriorityDownloadQueue,
        worker_factory: WorkerFactory | type[DownloadWorker],
        logger: "Logger",
        download_dir: Path,
        max_workers: int = 3,
        event_wiring: EventWiring | None = None,
        file_exists_strategy: FileExistsStrategy = FileExistsStrategy.SKIP,
        emitter: BaseEmitter | None = None,
        retry_handler: BaseRetryHandler | None = None,
    ) -> None:
        """Initialise the worker pool.

        Args:
            queue: Priority queue for retrieving download tasks.
            worker_factory: Factory function or class for creating worker instances.
                          Called with (client, logger, emitter) and must return
                          a BaseWorker instance.
            logger: Logger instance for recording pool events and worker activity
            download_dir: Directory where downloaded files will be saved
            max_workers: Maximum number of concurrent worker tasks. Defaults to 3.
            event_wiring: Event handlers categorised by EventSource. Structure:
                         {"queue": {...}, "worker": {...}}. If None, no events
                         are wired.
            file_exists_strategy: Default strategy for handling existing files.
                         Per-file strategy in FileConfig overrides this.
            emitter: Shared event emitter for queue and worker events. If None,
                     a new EventEmitter is created.
        """
        self.queue = queue
        self._worker_factory = worker_factory
        self._logger = logger
        self._download_dir = download_dir
        self._max_workers = max_workers
        self._shutdown_event = asyncio.Event()
        self._worker_tasks: list[asyncio.Task[None]] = []
        self._is_running = False
        self._event_wiring = event_wiring or {
            EventSource.QUEUE: {},
            EventSource.WORKER: {},
        }
        self._file_exists_strategy = file_exists_strategy
        self._emitter = emitter or EventEmitter(self._logger)
        self._retry_handler = retry_handler or NullRetryHandler()
        # Track active download tasks by download_id, used for cancellation.
        self._active_download_tasks: dict[str, asyncio.Task[None]] = {}
        # IDs of downloads cancelled while queued, checked before starting download.
        self._cancelled_ids: set[str] = set()

    @property
    def active_tasks(self) -> tuple[asyncio.Task[None], ...]:
        """Snapshot of currently running worker tasks.

        Returns immutable tuple for safe inspection without affecting pool state.
        """
        return tuple(self._worker_tasks)

    @property
    def active_download_tasks(self) -> dict[str, asyncio.Task[None]]:
        """Snapshot of currently active download tasks by download_id."""
        return self._active_download_tasks.copy()

    @property
    def is_running(self) -> bool:
        """True if pool has been started and not yet stopped."""
        return self._is_running

    async def start(self, client: BaseHttpClient) -> None:
        """Start worker tasks that process the download queue.

        Creates max_workers tasks, each with its own worker instance and emitter.
        Workers begin polling the queue immediately.

        Args:
            client: Initialised HTTP client for making requests

        Raises:
            WorkerPoolAlreadyStartedError: If pool is already running
        """
        if self._is_running:
            raise WorkerPoolAlreadyStartedError("WorkerPool already started")

        self._shutdown_event.clear()
        self._is_running = True

        # Wire queue events once at startup
        self._wire_queue_events()
        # Wire worker events once to shared emitter
        self._wire_worker_events()

        for _ in range(self._max_workers):
            worker = self.create_worker(client)
            task = asyncio.create_task(self._process_queue(worker))
            self._worker_tasks.append(task)

    async def shutdown(self, wait_for_current: bool = True) -> None:
        """Initiate graceful shutdown of all workers.

        Args:
            wait_for_current: If True, allow in-flight downloads to complete before
                            stopping. If False, cancel all worker tasks immediately.
        """
        self._request_shutdown()

        if not wait_for_current:
            # Cancel all tasks (downloads and workers) for immediate shutdown
            for task in self._active_download_tasks.values():
                task.cancel()
            for task in self._worker_tasks:
                task.cancel()

        # Wait for workers to finish (either gracefully or after cancellation)
        # and clean up task references
        await self._wait_for_workers_and_clear()

    async def cancel(self, download_id: str) -> bool:
        """Cancel a specific download by ID.

        Handles both in-progress downloads (via task cancellation) and
        queued downloads (via cooperative cancellation).

        Args:
            download_id: The download ID to cancel

        Returns:
            True if download was active or queued and cancelled.
            False if download_id is not known to the pool (may be terminal or
            never existed - caller should check tracker).
        """
        # Check if download is currently in progress
        task = self._active_download_tasks.get(download_id)
        if task is not None:
            task.cancel()
            return True

        # Check if download is queued but not yet started
        if download_id in self.queue._queued_ids:
            self._cancelled_ids.add(download_id)
            return True

        # Not in pool's scope so let caller determine why
        return False

    def _request_shutdown(self) -> None:
        """Signal workers to stop accepting new work.

        Idempotent - safe to call multiple times. Workers will complete their
        current download (if any) and then exit their processing loop.
        """
        self._shutdown_event.set()

    def create_worker(self, client: BaseHttpClient) -> BaseWorker:
        """Create a worker instance with shared emitter.

        Args:
            client: HTTP client to inject into worker

        Returns:
            Fully configured worker instance ready to process downloads

        Note:
            This method is public to support testing and custom worker creation
            scenarios, but is typically called only by start().
        """
        return self._worker_factory(
            client,
            self._logger,
            self._emitter,
            default_file_exists_strategy=self._file_exists_strategy,
            retry_handler=self._retry_handler,
        )

    def _wire_queue_events(self) -> None:
        """Wire queue events to provided handlers."""
        for event_type, handler in self._event_wiring.get(
            EventSource.QUEUE, {}
        ).items():
            self.queue.emitter.on(event_type, handler)

    def _wire_worker_events(self) -> None:
        """Wire worker events to provided handlers on shared emitter."""
        for event_type, handler in self._event_wiring.get(
            EventSource.WORKER, {}
        ).items():
            self._emitter.on(event_type, handler)

    async def _process_queue(self, worker: BaseWorker) -> None:
        """Process downloads from queue until shutdown or cancellation.

        Uses event-based shutdown mechanism to allow graceful termination.
        Workers periodically check the shutdown event and can complete current
        downloads before exiting.

        Args:
            worker: The worker instance to use for downloads in this task
        """
        while not self._shutdown_event.is_set():
            file_config: FileConfig | None = None
            got_item = False
            try:
                # Use timeout to prevent indefinite blocking on empty queue.
                # Without timeout, worker would be stuck waiting and couldn't
                # respond to shutdown until a new item arrives. The 1-second
                # timeout allows checking shutdown event every second maximum.
                file_config = await asyncio.wait_for(self.queue.get_next(), timeout=1.0)
                got_item = True

                destination_path = file_config.get_destination_path(self._download_dir)

                # Check shutdown before starting download to prevent race condition.
                # This ensures we don't start downloads after shutdown is triggered.
                if await self._handle_shutdown_and_requeue(file_config):
                    break

                # Check if this download was cancelled while queued
                if await self._handle_cancelled_queued(file_config):
                    continue

                self._logger.debug(
                    f"Downloading {file_config.url} to {destination_path}"
                )

                cancelled = await self._execute_download(
                    worker, file_config, destination_path
                )
                if cancelled:
                    continue

                self._logger.debug(
                    f"Downloaded {file_config.url} to {destination_path}"
                )
            except asyncio.TimeoutError:
                # No item available within timeout period. This is normal when
                # queue is empty or all items were taken by other workers.
                # Loop continues to check shutdown event and retry.
                continue
            except asyncio.CancelledError:
                # Raised when task.cancel() is called (immediate shutdown).
                # Must re-raise to properly terminate the task, otherwise
                # asyncio considers cancellation "handled" and keeps running.
                self._logger.debug("Worker cancelled, stopping immediately")
                raise
            except Exception as exc:
                # file_config may not be defined if error getting from queue.
                url = file_config.url if file_config else "unknown"
                self._logger.error(
                    f"Failed to download {url}: {type(exc).__name__}: {exc}"
                )
                # Continue processing other items instead of crashing.
                # Error details are already logged by the worker.
            finally:
                # Only call task_done if we actually got an item.
                # Pass download_id to allow re-queueing the same download later.
                if got_item and file_config:
                    self.queue.task_done(file_config.id)

        self._logger.debug("Worker shutting down gracefully")

    async def _handle_shutdown_and_requeue(self, file_config: FileConfig) -> bool:
        """Check shutdown and requeue item if shutdown is active.

        This helper consolidates the shutdown check and requeue logic used at
        the point between retrieving an item and starting its download. When
        shutdown is detected, the item is returned to the queue and task_done()
        is called to maintain queue accounting balance.

        Args:
            file_config: The file configuration to requeue if shutting down

        Returns:
            True if shutdown was detected (caller should break), False otherwise
        """
        shutdown_is_set = self._shutdown_event.is_set()
        if shutdown_is_set:
            # Put item back in queue if shutting down, then call task_done()
            # to balance the accounting. The get() incremented the unfinished
            # task counter, so we must decrement it even though we're re-queuing.
            # Without task_done(), queue.join() would hang waiting for this item.
            await self.queue.add([file_config])
            self.queue.task_done(file_config.id)
        return shutdown_is_set

    async def _handle_cancelled_queued(self, file_config: FileConfig) -> bool:
        """Check if download was cancelled while queued and handle if so.

        If the download ID is in _cancelled_ids, emits a cancelled event,
        and signals caller to skip this download.

        Args:
            file_config: The file configuration to check

        Returns:
            True if download was cancelled (caller should continue), False otherwise
        """
        if file_config.id not in self._cancelled_ids:
            return False

        self._cancelled_ids.discard(file_config.id)

        self._logger.debug(f"Skipping cancelled download: {file_config.url}")

        await self._emitter.emit(
            "download.cancelled",
            DownloadCancelledEvent(
                download_id=file_config.id,
                url=str(file_config.url),
                cancelled_from=CancelledFrom.QUEUED,
            ),
        )

        return True

    async def _execute_download(
        self,
        worker: BaseWorker,
        file_config: FileConfig,
        destination_path: Path,
    ) -> bool:
        """Execute download as a tracked task with cancellation support.

        Creates an asyncio task for the download, tracks it in _active_download_tasks,
        and handles cancellation. Individual download cancellation (via pool.cancel())
        is distinguished from worker shutdown cancellation.

        Args:
            worker: The worker instance to use for the download
            file_config: Configuration for the file to download
            destination_path: Local path to save the file

        Returns:
            True if the download was cancelled (caller should continue to next item),
            False if completed normally

        Raises:
            asyncio.CancelledError: If the worker task itself was cancelled (shutdown)
        """
        download_task = asyncio.create_task(
            worker.download(
                str(file_config.url),
                destination_path,
                download_id=file_config.id,
                hash_config=file_config.hash_config,
                file_exists_strategy=file_config.file_exists_strategy,
            )
        )
        self._active_download_tasks[file_config.id] = download_task

        try:
            await download_task
            return False
        except asyncio.CancelledError:
            # Distinguish between individual download cancellation and worker shutdown.
            # If download_task.cancelled() is True, this specific download was cancelled
            # via pool.cancel(). Otherwise, the worker task itself was cancelled.
            if download_task.cancelled():
                self._logger.debug(f"Download cancelled: {file_config.url}")
                return True
            raise
        finally:
            self._active_download_tasks.pop(file_config.id, None)

    async def _wait_for_workers_and_clear(self) -> None:
        """Wait for all worker tasks to complete and clear the task list.

        Handles exceptions gracefully via return_exceptions=True.
        Sets is_running to False after all tasks have finished.
        """
        if not self._worker_tasks:
            self._is_running = False
            return

        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        self._is_running = False
