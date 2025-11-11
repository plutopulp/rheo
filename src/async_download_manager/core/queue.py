"""Priority queue for managing download tasks.

This module provides a PriorityDownloadQueue class that wraps asyncio.PriorityQueue
and provides a clean interface for managing file downloads with priority ordering.
"""

import asyncio
import typing as t
from typing import TYPE_CHECKING

from .logger import get_logger
from .models import FileConfig

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
    """

    def __init__(
        self,
        queue: asyncio.PriorityQueue[tuple[int, int, FileConfig]] | None = None,
        logger: t.Optional["loguru.Logger"] = None,
    ) -> None:
        """Initialize the priority download queue.

        Args:
            queue: Optional asyncio.PriorityQueue instance. If None, one will be created.
                  This enables dependency injection for better testability.
            logger: Logger instance for recording queue events. If None,
                   a default logger will be created.
        """
        self._queue = queue or asyncio.PriorityQueue()
        self._logger = logger or get_logger(__name__)
        self._counter = 0  # Counter to maintain FIFO order for same priority items

    async def add(self, file_configs: t.Sequence[FileConfig]) -> None:
        """Add file configurations to the priority queue.

        Items are added with priority ordering - higher priority values
        will be retrieved first. Items with equal priority maintain
        FIFO (first-in-first-out) ordering.

        Args:
            file_configs: Sequence of FileConfig objects to add to the queue.
        """
        for file_config in file_configs:
            self._logger.info(f"Adding {file_config.url} to the queue")
            # Negate priority for min-heap behavior (higher priority = lower number)
            # Use counter as tiebreaker to maintain FIFO order for same priority
            await self._queue.put((-file_config.priority, self._counter, file_config))
            self._counter += 1

    async def get_next(self) -> FileConfig:
        """Get the next highest priority item from the queue.

        This method will block until an item is available. Items are returned
        in priority order (highest priority first).

        Returns:
            The FileConfig object with the highest priority.
        """
        self._logger.info("Waiting for a file config to be available from the queue...")
        _, _, file_config = await self._queue.get()
        return file_config

    def task_done(self) -> None:
        """Mark a task as completed.

        Should be called after processing each item retrieved from the queue.
        This is required for proper queue.join() behavior.
        """
        self._queue.task_done()

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
