"""Download tracking system for state management.

This tracker stores download state and provides query methods.
It does NOT emit events. Events are emitted by the worker (download.* namespace).
The tracker is an observer that receives state updates from the pool's event wiring.
"""

import asyncio
import typing as t
from collections import Counter

from ..domain.downloads import DownloadInfo, DownloadStats, DownloadStatus
from ..domain.hash_validation import ValidationResult
from ..domain.speed import SpeedMetrics
from ..infrastructure.logging import get_logger
from .base import BaseTracker

# Conditional import for loguru typing
if t.TYPE_CHECKING:
    import loguru


class DownloadTracker(BaseTracker):
    """Tracks download state for query and aggregation.

    Maintains a dictionary of DownloadInfo objects keyed by download_id.
    Thread-safe for concurrent access from multiple workers.

    This tracker is an observer. It receives state updates from the pool's
    event wiring but does NOT emit events. Events are emitted by the worker
    using the download.* namespace. Subscribe to events via the manager or
    worker emitter directly.

    Usage:
        tracker = DownloadTracker()

        # State is updated by pool event wiring (not directly by user)
        # Pool wires: download.started -> tracker._track_started()

        # Query state
        info = tracker.get_download_info(download_id)
        print(f"Status: {info.status}, Progress: {info.get_progress()}")

        # Get statistics
        stats = tracker.get_stats()
        print(f"Completed: {stats.completed}, Failed: {stats.failed}")
    """

    def __init__(
        self,
        logger: "loguru.Logger" = get_logger(__name__),
    ):
        """Initialize empty tracker.

        Args:
            logger: Logger instance for debugging and error tracking.
                   Defaults to a module-specific logger if not provided.
        """
        self._downloads: dict[str, DownloadInfo] = {}
        self._speed_metrics: dict[str, SpeedMetrics] = {}
        self._lock = asyncio.Lock()
        self._logger = logger

        self._logger.debug("DownloadTracker initialised")

    async def _track_queued(
        self, download_id: str, url: str, priority: int = 1
    ) -> None:
        """Record that a download was queued.

        Creates a new DownloadInfo with QUEUED status.

        Args:
            download_id: Unique identifier for this download task
            url: The URL being downloaded
            priority: Priority level for the download (stored for reference)
        """
        async with self._lock:
            self._downloads[download_id] = DownloadInfo(
                id=download_id, url=url, status=DownloadStatus.QUEUED
            )

    async def _track_started(
        self, download_id: str, url: str, total_bytes: int | None = None
    ) -> None:
        """Record that a download started.

        Updates status to IN_PROGRESS and sets total_bytes if known.

        Args:
            download_id: Unique identifier for this download task
            url: The URL being downloaded
            total_bytes: Total size in bytes (optional)
        """
        async with self._lock:
            if download_id not in self._downloads:
                self._downloads[download_id] = DownloadInfo(id=download_id, url=url)

            self._downloads[download_id].status = DownloadStatus.IN_PROGRESS
            if total_bytes is not None:
                self._downloads[download_id].total_bytes = total_bytes

    async def _track_progress(
        self,
        download_id: str,
        url: str,
        bytes_downloaded: int,
        total_bytes: int | None = None,
        speed: SpeedMetrics | None = None,
    ) -> None:
        """Update download progress with optional speed metrics.

        Updates bytes_downloaded and optionally total_bytes, and stores speed
        metrics snapshot when provided. Speed metrics are cleared on completion
        or failure.

        Args:
            download_id: Unique identifier for this download task
            url: The URL being downloaded
            bytes_downloaded: Bytes downloaded so far
            total_bytes: Total size in bytes (optional)
            speed: Speed metrics snapshot (optional)
        """
        async with self._lock:
            if download_id not in self._downloads:
                self._downloads[download_id] = DownloadInfo(id=download_id, url=url)

            self._downloads[download_id].bytes_downloaded = bytes_downloaded
            if total_bytes is not None:
                self._downloads[download_id].total_bytes = total_bytes

            if speed is not None:
                self._speed_metrics[download_id] = speed

    def get_speed_metrics(self, download_id: str) -> SpeedMetrics | None:
        """Get current speed metrics for a download.

        Args:
            download_id: The download ID to query

        Returns:
            SpeedMetrics if available, None otherwise
        """
        return self._speed_metrics.get(download_id)

    def _ensure_download_exists(self, download_id: str, url: str) -> None:
        """Ensure DownloadInfo exists for download, create if missing.

        Must be called within _lock context.

        Args:
            download_id: Unique identifier for this download task
            url: The URL being downloaded
        """
        if download_id not in self._downloads:
            self._downloads[download_id] = DownloadInfo(id=download_id, url=url)

    def _capture_and_clear_final_speed(self, download_id: str) -> float | None:
        """Capture final average speed and clear transient metrics.

        Extracts the average speed from transient metrics for persistence,
        then clears the transient metrics to free memory.

        Must be called within _lock context.

        Args:
            download_id: The download ID to capture speed for

        Returns:
            Final average speed in bytes/second, or None if no metrics exist
        """
        final_speed = None
        if download_id in self._speed_metrics:
            final_speed = self._speed_metrics[download_id].average_speed_bps

        # Clear transient speed metrics
        self._speed_metrics.pop(download_id, None)

        return final_speed

    async def _track_completed(
        self,
        download_id: str,
        url: str,
        total_bytes: int = 0,
        destination_path: str | None = None,
        validation: ValidationResult | None = None,
    ) -> None:
        """Record that a download completed successfully.

        Sets status to COMPLETED and updates final byte count.
        Stores validation result directly if provided.
        Persists average speed from final metrics, then clears transient metrics.

        Args:
            download_id: Unique identifier for this download task
            url: The URL that was downloaded
            total_bytes: Final size in bytes
            destination_path: Where the file was saved (stored for reference)
            validation: Optional validation result from hash verification
        """
        async with self._lock:
            self._ensure_download_exists(download_id, url)
            final_speed = self._capture_and_clear_final_speed(download_id)

            self._downloads[download_id].status = DownloadStatus.COMPLETED
            self._downloads[download_id].bytes_downloaded = total_bytes
            self._downloads[download_id].total_bytes = total_bytes
            self._downloads[download_id].average_speed_bps = final_speed
            self._downloads[download_id].destination_path = destination_path
            self._downloads[download_id].validation = validation

    async def _track_failed(
        self,
        download_id: str,
        url: str,
        error: Exception,
        validation: ValidationResult | None = None,
    ) -> None:
        """Record that a download failed.

        Sets status to FAILED and stores error message.
        Stores validation result directly if provided (e.g., hash mismatch).
        Persists average speed from metrics if available (useful for failure analysis).
        Clears transient speed metrics.

        Args:
            download_id: Unique identifier for this download task
            url: The URL that failed
            error: The exception that occurred
            validation: Optional validation result when failure is hash mismatch
        """
        async with self._lock:
            self._ensure_download_exists(download_id, url)
            final_speed = self._capture_and_clear_final_speed(download_id)

            self._downloads[download_id].status = DownloadStatus.FAILED
            self._downloads[download_id].error = str(error)
            self._downloads[download_id].average_speed_bps = final_speed
            self._downloads[download_id].validation = validation

    async def _track_skipped(
        self,
        download_id: str,
        url: str,
        reason: str,
        destination_path: str | None = None,
    ) -> None:
        """Record that a download was skipped."""
        async with self._lock:
            self._downloads[download_id] = DownloadInfo(
                id=download_id,
                url=url,
                status=DownloadStatus.SKIPPED,
                destination_path=destination_path,
            )

    async def _track_cancelled(self, download_id: str, url: str) -> None:
        """Record that a download was cancelled."""
        async with self._lock:
            self._ensure_download_exists(download_id, url)
            self._downloads[download_id].status = DownloadStatus.CANCELLED
            self._speed_metrics.pop(download_id, None)

    def get_download_info(self, download_id: str) -> DownloadInfo | None:
        """Get current state of a download.

        Args:
            download_id: The download ID to query

        Returns:
            DownloadInfo if found, None otherwise
        """
        return self._downloads.get(download_id)

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
            queued=statuses[DownloadStatus.QUEUED],
            in_progress=statuses[DownloadStatus.IN_PROGRESS],
            completed=statuses[DownloadStatus.COMPLETED],
            failed=statuses[DownloadStatus.FAILED],
            cancelled=statuses[DownloadStatus.CANCELLED],
            completed_bytes=completed_bytes,
        )
