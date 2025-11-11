"""Download tracking system with event emission.

This tracker stores download state and emits events for lifecycle changes.
"""

import asyncio
import typing as t
from collections import Counter

from .events import (
    DownloadCompletedEvent,
    DownloadEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadStartedEvent,
)
from .logger import get_logger
from .models import DownloadInfo, DownloadStats, DownloadStatus

# Conditional import for loguru typing
if t.TYPE_CHECKING:
    import loguru

# Type alias for event handlers
EventHandler = t.Callable[[DownloadEvent], t.Any]


class DownloadTracker:
    """Tracks download state and emits events for lifecycle changes.

    Maintains a dictionary of DownloadInfo objects keyed by URL.
    Thread-safe for concurrent access from multiple workers.
    Supports event subscription for observing download lifecycle.

    Usage:
        tracker = DownloadTracker()

        # Subscribe to events
        tracker.on("progress", my_progress_handler)
        tracker.on("completed", my_completion_handler)

        # Update state (automatically emits events)
        await tracker.track_queued("https://example.com/file.txt")
        await tracker.track_started("https://example.com/file.txt", total_bytes=1024)
        await tracker.track_progress("https://example.com/file.txt",
                                     bytes_downloaded=512,
                                     total_bytes=1024)
        await tracker.track_completed("https://example.com/file.txt", total_bytes=1024)

        # Query state
        info = tracker.get_download_info("https://example.com/file.txt")
        print(f"Status: {info.status}, Progress: {info.get_progress()}")
    """

    def __init__(self, logger: "loguru.Logger" = get_logger(__name__)):
        """Initialize empty tracker.

        Args:
            logger: Logger instance for debugging and error tracking.
                   Defaults to a module-specific logger if not provided.
        """
        self._downloads: dict[str, DownloadInfo] = {}
        self._event_handlers: dict[str, list[EventHandler]] = {}
        self._lock = asyncio.Lock()
        self._logger = logger

        self._logger.debug("DownloadTracker initialized")

    def on(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to download events.

        Args:
            event_type: Type of event to listen for (queued, started, progress,
                       completed, failed, or "*" for all events)
            handler: Callback function (can be sync or async)

        Example:
            def on_progress(event: DownloadProgressEvent):
                print(f"Downloaded {event.progress_percent:.1f}%")

            tracker.on("progress", on_progress)
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def off(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from download events.

        Args:
            event_type: Type of event to stop listening for
            handler: The handler function to remove
        """
        try:
            self._event_handlers[event_type].remove(handler)
        except Exception:
            self._logger.warning(
                f"Handler {handler} not found for event type {event_type}"
            )
            pass

    async def _emit(self, event: DownloadEvent) -> None:
        """Emit an event to all subscribed handlers.

        Handles both sync and async handlers. Runs handlers concurrently
        where possible for better performance.

        Args:
            event: The event to emit
        """
        # Get handlers for this specific event type and wildcard handlers
        handlers = self._event_handlers.get(event.event_type, []).copy()
        handlers.extend(self._event_handlers.get("*", []))

        # Run all handlers (supporting both sync and async)
        tasks = []
        for handler in handlers:
            try:
                result = handler(event)
                # If handler is async, create a task for it
                if asyncio.iscoroutine(result):
                    tasks.append(result)
            except Exception:
                # Log handler exceptions with full traceback for debugging
                self._logger.exception(
                    f"Error in event handler for {event.event_type} event"
                )

        # Await all async handlers and log any exceptions
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Log any exceptions that occurred in async handlers
            for result in results:
                if isinstance(result, Exception):
                    # Loguru's opt() allows us to pass exception info
                    self._logger.opt(
                        exception=(type(result), result, result.__traceback__)
                    ).error(
                        f"Error in async event handler for {event.event_type} event"
                    )

    async def track_queued(self, url: str, priority: int = 1) -> None:
        """Record that a download was queued.

        Creates a new DownloadInfo with QUEUED status and emits DownloadQueuedEvent.

        Args:
            url: The URL being queued
            priority: Priority level for the download
        """
        async with self._lock:
            self._downloads[url] = DownloadInfo(url=url, status=DownloadStatus.QUEUED)

        await self._emit(DownloadQueuedEvent(url=url, priority=priority))

    async def track_started(self, url: str, total_bytes: int | None = None) -> None:
        """Record that a download started.

        Updates status to IN_PROGRESS and sets total_bytes if known.
        Emits DownloadStartedEvent.

        Args:
            url: The URL being downloaded
            total_bytes: Total size in bytes (optional)
        """
        async with self._lock:
            if url not in self._downloads:
                self._downloads[url] = DownloadInfo(url=url)

            self._downloads[url].status = DownloadStatus.IN_PROGRESS
            if total_bytes is not None:
                self._downloads[url].total_bytes = total_bytes

        await self._emit(DownloadStartedEvent(url=url, total_bytes=total_bytes))

    async def track_progress(
        self, url: str, bytes_downloaded: int, total_bytes: int | None = None
    ) -> None:
        """Update download progress.

        Updates bytes_downloaded and optionally total_bytes.
        Emits DownloadProgressEvent.

        Args:
            url: The URL being downloaded
            bytes_downloaded: Bytes downloaded so far
            total_bytes: Total size in bytes (optional)
        """
        async with self._lock:
            if url not in self._downloads:
                self._downloads[url] = DownloadInfo(url=url)

            self._downloads[url].bytes_downloaded = bytes_downloaded
            if total_bytes is not None:
                self._downloads[url].total_bytes = total_bytes

        await self._emit(
            DownloadProgressEvent(
                url=url, bytes_downloaded=bytes_downloaded, total_bytes=total_bytes
            )
        )

    async def track_completed(
        self, url: str, total_bytes: int = 0, destination_path: str = ""
    ) -> None:
        """Record that a download completed successfully.

        Sets status to COMPLETED and updates final byte count.
        Emits DownloadCompletedEvent.

        Args:
            url: The URL that was downloaded
            total_bytes: Final size in bytes
            destination_path: Where the file was saved
        """
        async with self._lock:
            if url not in self._downloads:
                self._downloads[url] = DownloadInfo(url=url)

            self._downloads[url].status = DownloadStatus.COMPLETED
            self._downloads[url].bytes_downloaded = total_bytes
            self._downloads[url].total_bytes = total_bytes

        await self._emit(
            DownloadCompletedEvent(
                url=url, total_bytes=total_bytes, destination_path=destination_path
            )
        )

    async def track_failed(self, url: str, error: Exception) -> None:
        """Record that a download failed.

        Sets status to FAILED and stores error message.
        Emits DownloadFailedEvent.

        Args:
            url: The URL that failed
            error: The exception that occurred
        """
        async with self._lock:
            if url not in self._downloads:
                self._downloads[url] = DownloadInfo(url=url)

            self._downloads[url].status = DownloadStatus.FAILED
            self._downloads[url].error = str(error)

        await self._emit(
            DownloadFailedEvent(
                url=url, error_message=str(error), error_type=type(error).__name__
            )
        )

    def get_download_info(self, url: str) -> DownloadInfo | None:
        """Get current state of a download.

        Args:
            url: The URL to query

        Returns:
            DownloadInfo if found, None otherwise
        """
        return self._downloads.get(url)

    def get_all_downloads(self) -> dict[str, DownloadInfo]:
        """Get state of all tracked downloads.

        Returns:
            Copy of the downloads dictionary
        """
        return self._downloads.copy()

    def get_active_downloads(self) -> dict[str, DownloadInfo]:
        """Get all downloads currently in progress.

        Returns:
            Dictionary of downloads with IN_PROGRESS status
        """
        return {
            url: info
            for url, info in self._downloads.items()
            if info.status == DownloadStatus.IN_PROGRESS
        }

    def get_stats(self) -> DownloadStats:
        """Get summary statistics about all downloads.

        Returns:
            Dictionary with counts by status and overall stats
        """
        download_infos = list(self._downloads.values())

        statuses: Counter[DownloadStatus] = Counter(
            info.status for info in download_infos
        )

        completed_bytes = sum(
            info.total_bytes or 0
            for info in download_infos
            if info.status == DownloadStatus.COMPLETED
        )

        return DownloadStats(
            total=len(download_infos),
            queued=statuses.get(DownloadStatus.QUEUED, 0),
            in_progress=statuses.get(DownloadStatus.IN_PROGRESS, 0),
            completed=statuses.get(DownloadStatus.COMPLETED, 0),
            failed=statuses.get(DownloadStatus.FAILED, 0),
            completed_bytes=completed_bytes,
        )
