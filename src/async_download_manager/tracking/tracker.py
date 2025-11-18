"""Download tracking system with event emission.

This tracker stores download state and emits events for lifecycle changes.
"""

import asyncio
import typing as t
from collections import Counter

from ..domain.downloads import DownloadInfo, DownloadStats, DownloadStatus
from ..domain.hash_validation import ValidationState, ValidationStatus
from ..domain.speed import SpeedMetrics
from ..events import (
    DownloadCompletedEvent,
    DownloadEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadStartedEvent,
    DownloadValidationCompletedEvent,
    DownloadValidationFailedEvent,
    DownloadValidationStartedEvent,
    EventEmitter,
)
from ..infrastructure.logging import get_logger
from .base import BaseTracker

# Conditional import for loguru typing
if t.TYPE_CHECKING:
    import loguru

# Type alias for event handlers
EventHandler = t.Callable[[DownloadEvent], t.Any]


class DownloadTracker(BaseTracker):
    """Tracks download state and emits events for lifecycle changes.

    Maintains a dictionary of DownloadInfo objects keyed by URL.
    Thread-safe for concurrent access from multiple workers.
    Supports event subscription for observing download lifecycle.

    Usage:
        tracker = DownloadTracker()

        # Subscribe to events (with namespaced event types)
        tracker.on("tracker.progress", my_progress_handler)
        tracker.on("tracker.completed", my_completion_handler)

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

    def __init__(
        self,
        logger: "loguru.Logger" = get_logger(__name__),
        emitter: EventEmitter | None = None,
    ):
        """Initialize empty tracker.

        Args:
            logger: Logger instance for debugging and error tracking.
                   Defaults to a module-specific logger if not provided.
            emitter: Event emitter for broadcasting tracker events.
                    If None, a new EventEmitter will be created.
        """
        self._downloads: dict[str, DownloadInfo] = {}
        self._speed_metrics: dict[str, SpeedMetrics] = {}
        self._lock = asyncio.Lock()
        self._logger = logger
        self._emitter = emitter if emitter is not None else EventEmitter(logger)

        self._logger.debug("DownloadTracker initialized")

    @property
    def emitter(self) -> EventEmitter:
        """Event emitter for tracker events."""
        return self._emitter

    def on(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to download events.

        Args:
            event_type: Type of event to listen for (tracker.queued, tracker.started,
                       tracker.progress, tracker.completed, tracker.failed)
            handler: Callback function (can be sync or async)

        Example:
            def on_progress(event: DownloadProgressEvent):
                print(f"Downloaded {event.progress_percent:.1f}%")

            tracker.on("tracker.progress", on_progress)
        """
        self._emitter.on(event_type, handler)

    def off(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from download events.

        Args:
            event_type: Type of event to stop listening for
            handler: The handler function to remove
        """
        self._emitter.off(event_type, handler)

    async def _emit(self, event_type: str, event: DownloadEvent) -> None:
        """Emit an event to all subscribed handlers via EventEmitter.

        Args:
            event_type: Namespaced event type (e.g., "tracker.queued")
            event: The event data to emit
        """
        await self._emitter.emit(event_type, event)

    async def track_queued(self, url: str, priority: int = 1) -> None:
        """Record that a download was queued.

        Creates a new DownloadInfo with QUEUED status and emits DownloadQueuedEvent.

        Args:
            url: The URL being queued
            priority: Priority level for the download
        """
        async with self._lock:
            self._downloads[url] = DownloadInfo(url=url, status=DownloadStatus.QUEUED)

        await self._emit(
            "tracker.queued", DownloadQueuedEvent(url=url, priority=priority)
        )

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

        await self._emit(
            "tracker.started", DownloadStartedEvent(url=url, total_bytes=total_bytes)
        )

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
            "tracker.progress",
            DownloadProgressEvent(
                url=url, bytes_downloaded=bytes_downloaded, total_bytes=total_bytes
            ),
        )

    async def track_speed_update(
        self,
        url: str,
        current_speed_bps: float,
        average_speed_bps: float,
        eta_seconds: float | None,
        elapsed_seconds: float,
    ) -> None:
        """Update speed metrics for a download.

        Stores the latest speed and ETA information for active downloads.
        Speed metrics are cleared when download completes or fails.

        Args:
            url: The URL being downloaded
            current_speed_bps: Instantaneous speed in bytes per second
            average_speed_bps: Moving average speed in bytes per second
            eta_seconds: Estimated time to completion in seconds (None if unknown)
            elapsed_seconds: Time elapsed since download started in seconds
        """
        async with self._lock:
            self._speed_metrics[url] = SpeedMetrics(
                current_speed_bps=current_speed_bps,
                average_speed_bps=average_speed_bps,
                eta_seconds=eta_seconds,
                elapsed_seconds=elapsed_seconds,
            )

    def get_speed_metrics(self, url: str) -> SpeedMetrics | None:
        """Get current speed metrics for a download.

        Args:
            url: The URL to query

        Returns:
            SpeedMetrics if available, None otherwise
        """
        return self._speed_metrics.get(url)

    def _ensure_download_exists(self, url: str) -> None:
        """Ensure DownloadInfo exists for URL, create if missing.

        Must be called within _lock context.

        Args:
            url: The URL to ensure exists in tracking
        """
        if url not in self._downloads:
            self._downloads[url] = DownloadInfo(url=url)

    def _capture_and_clear_final_speed(self, url: str) -> float | None:
        """Capture final average speed and clear transient metrics.

        Extracts the average speed from transient metrics for persistence,
        then clears the transient metrics to free memory.

        Must be called within _lock context.

        Args:
            url: The URL to capture speed for

        Returns:
            Final average speed in bytes/second, or None if no metrics exist
        """
        final_speed = None
        if url in self._speed_metrics:
            final_speed = self._speed_metrics[url].average_speed_bps

        # Clear transient speed metrics
        self._speed_metrics.pop(url, None)

        return final_speed

    async def track_completed(
        self, url: str, total_bytes: int = 0, destination_path: str = ""
    ) -> None:
        """Record that a download completed successfully.

        Sets status to COMPLETED and updates final byte count.
        Persists average speed from final metrics, then clears transient metrics.
        Emits DownloadCompletedEvent.

        Args:
            url: The URL that was downloaded
            total_bytes: Final size in bytes
            destination_path: Where the file was saved
        """
        async with self._lock:
            self._ensure_download_exists(url)
            final_speed = self._capture_and_clear_final_speed(url)

            self._downloads[url].status = DownloadStatus.COMPLETED
            self._downloads[url].bytes_downloaded = total_bytes
            self._downloads[url].total_bytes = total_bytes
            self._downloads[url].average_speed_bps = final_speed

        await self._emit(
            "tracker.completed",
            DownloadCompletedEvent(
                url=url, total_bytes=total_bytes, destination_path=destination_path
            ),
        )

    async def track_failed(self, url: str, error: Exception) -> None:
        """Record that a download failed.

        Sets status to FAILED and stores error message.
        Persists average speed from metrics if available (useful for failure analysis).
        Clears transient speed metrics.
        Emits DownloadFailedEvent.

        Args:
            url: The URL that failed
            error: The exception that occurred
        """
        async with self._lock:
            self._ensure_download_exists(url)
            final_speed = self._capture_and_clear_final_speed(url)

            self._downloads[url].status = DownloadStatus.FAILED
            self._downloads[url].error = str(error)
            self._downloads[url].average_speed_bps = final_speed

        await self._emit(
            "tracker.failed",
            DownloadFailedEvent(
                url=url, error_message=str(error), error_type=type(error).__name__
            ),
        )

    async def track_validation_started(self, url: str, algorithm: str) -> None:
        """Record that validation has started for a download."""
        async with self._lock:
            self._ensure_download_exists(url)
            self._downloads[url].validation = ValidationState(
                status=ValidationStatus.IN_PROGRESS,
            )

        await self._emit(
            "tracker.validation_started",
            DownloadValidationStartedEvent(url=url, algorithm=algorithm),
        )

    async def track_validation_completed(
        self,
        url: str,
        algorithm: str,
        calculated_hash: str,
    ) -> None:
        """Record successful validation."""
        async with self._lock:
            self._ensure_download_exists(url)
            self._downloads[url].validation = ValidationState(
                status=ValidationStatus.SUCCEEDED,
                validated_hash=calculated_hash,
                error=None,
            )

        await self._emit(
            "tracker.validation_completed",
            DownloadValidationCompletedEvent(
                url=url,
                algorithm=algorithm,
                calculated_hash=calculated_hash,
            ),
        )

    async def track_validation_failed(
        self,
        url: str,
        algorithm: str,
        expected_hash: str,
        actual_hash: str | None,
        error_message: str,
    ) -> None:
        """Record failed validation attempt."""
        async with self._lock:
            self._ensure_download_exists(url)
            self._downloads[url].validation = ValidationState(
                status=ValidationStatus.FAILED,
                validated_hash=actual_hash,
                error=error_message,
            )

        await self._emit(
            "tracker.validation_failed",
            DownloadValidationFailedEvent(
                url=url,
                algorithm=algorithm,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                error_message=error_message,
            ),
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
