"""Priority queue for managing download tasks.

This module provides a PriorityDownloadQueue class that wraps asyncio.PriorityQueue
and provides a clean interface for managing file downloads with priority ordering.
"""

import asyncio
import typing as t
from typing import TYPE_CHECKING

from ..domain.file_config import FileConfig
from ..events import DownloadQueuedEvent, NullEmitter
from ..events.base import BaseEmitter
from ..infrastructure.logging import get_logger

if TYPE_CHECKING:
    import loguru


class PriorityDownloadQueue:
    """Priority-based download queue implementation.

    This queue manages FileConfig objects with priority ordering, where higher
    priority numbers indicate higher priority. The queue automatically handles
    priority negation for correct min-heap behavior.

    Key features:
    - Higher priority numbers = higher priority (5 > 3 > 1)
    - Thread-safe async operations
    - Automatic logging of queue operations
    - FIFO ordering for items with equal priority
    - Event emission when items are added (download.queued)
    """

    def __init__(
        self,
        queue: asyncio.PriorityQueue[tuple[int, int, FileConfig]] | None = None,
        logger: t.Optional["loguru.Logger"] = None,
        emitter: BaseEmitter | None = None,
    ) -> None:
        """Initialize the priority download queue.

        Args:
            queue: Optional asyncio.PriorityQueue instance. If None, one will be created.
                  This enables dependency injection for better testability.
            logger: Logger instance for recording queue events. If None,
                   a default logger will be created.
            emitter: Event emitter for download.queued events. If None,
                    a NullEmitter is used (no events emitted).
        """
        self._queue = queue or asyncio.PriorityQueue()
        self._logger = logger or get_logger(__name__)
        self._emitter = emitter or NullEmitter()
        self._counter = 0  # Counter to maintain FIFO order for same priority items
        self._queued_ids: set[str] = set()  # Track IDs to prevent duplicates

    @property
    def emitter(self) -> BaseEmitter:
        """Event emitter for queue events (download.queued)."""
        return self._emitter

    async def add(self, file_configs: t.Sequence[FileConfig]) -> None:
        """Add file configurations to the priority queue.

        Items are added with priority ordering - higher priority values
        will be retrieved first. Items with equal priority maintain
        FIFO (first-in-first-out) ordering.

        Duplicate detection: If a FileConfig with the same download ID
        (URL + destination) is already queued, the duplicate will be
        skipped and a warning logged.

        Args:
            file_configs: Sequence of FileConfig objects to add to the queue.
        """
        for file_config in file_configs:
            download_id = file_config.id
            # Skip if already queued
            if download_id in self._queued_ids:
                self._logger.warning(
                    f"Skipping duplicate download: {file_config.url} "
                    f"(already queued with ID {download_id}...)"
                )
                continue

            self._logger.debug(f"Adding {file_config.url} to the queue")
            # Negate priority for min-heap behavior (higher priority = lower number)
            # Use counter as tiebreaker to maintain FIFO order for same priority
            await self._queue.put((-file_config.priority, self._counter, file_config))
            self._queued_ids.add(download_id)
            self._counter += 1

            # Emit queued event
            await self._emitter.emit(
                "download.queued",
                DownloadQueuedEvent(
                    download_id=download_id,
                    url=str(file_config.url),
                    priority=file_config.priority,
                ),
            )

    async def get_next(self) -> FileConfig:
        """Get the next highest priority item from the queue.

        This method will block until an item is available. Items are returned
        in priority order (highest priority first).

        Returns:
            The FileConfig object with the highest priority.
        """
        self._logger.debug(
            "Waiting for a file config to be available from the queue..."
        )
        _, _, file_config = await self._queue.get()
        return file_config

    def task_done(self, download_id: str) -> None:
        """Mark a task as completed and remove from duplicate tracking.

        Should be called after processing each item retrieved from the queue.
        This is required for proper queue.join() behavior and to allow the
        same download to be queued again in the future.

        Args:
            download_id: The unique ID of the download being marked as complete.
                        This must be the ID from the FileConfig that was retrieved.

        Raises:
            KeyError: If download_id was never queued or already removed.
                     This indicates a logic error in task completion tracking.
        """
        # Remove from tracking first to raise error if ID not in queue
        # This catches logic errors before calling the underlying queue's task_done()
        self._queued_ids.remove(download_id)
        self._queue.task_done()

    @property
    def pending_count(self) -> int:
        """Number of downloads not yet completed.

        Includes both items waiting in queue AND items currently being
        downloaded (retrieved but not marked as done).
        """
        return len(self._queued_ids)

    def is_empty(self) -> bool:
        """Check if the queue is empty.

        Returns:
            True if the queue has no items, False otherwise.
        """
        return self._queue.empty()

    def size(self) -> int:
        """Get the current number of items in the queue.

        Returns:
            The number of items currently in the queue.
        """
        return self._queue.qsize()

    async def join(self) -> None:
        """Wait for all tasks in the queue to be completed.

        This will block until task_done() has been called for each
        item that was added to the queue.
        """
        await self._queue.join()
