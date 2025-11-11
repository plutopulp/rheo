"""Download tracking system - Phase 1: State management only.

This tracker stores and queries download state without events (events come in Phase 2).
"""

import asyncio
from collections import Counter

from .models import DownloadInfo, DownloadStats, DownloadStatus


class DownloadTracker:
    """Tracks download state without event emission.

    Maintains a dictionary of DownloadInfo objects keyed by URL.
    Thread-safe for concurrent access from multiple workers.

    Usage:
        tracker = DownloadTracker()

        # Update state
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

    def __init__(self):
        """Initialize empty tracker."""
        self._downloads: dict[str, DownloadInfo] = {}
        self._lock = asyncio.Lock()

    async def track_queued(self, url: str) -> None:
        """Record that a download was queued.

        Creates a new DownloadInfo with QUEUED status.

        Args:
            url: The URL being queued
        """
        async with self._lock:
            self._downloads[url] = DownloadInfo(url=url, status=DownloadStatus.QUEUED)

    async def track_started(self, url: str, total_bytes: int | None = None) -> None:
        """Record that a download started.

        Updates status to IN_PROGRESS and sets total_bytes if known.

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

    async def track_progress(
        self, url: str, bytes_downloaded: int, total_bytes: int | None = None
    ) -> None:
        """Update download progress.

        Updates bytes_downloaded and optionally total_bytes.

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

    async def track_completed(self, url: str, total_bytes: int = 0) -> None:
        """Record that a download completed successfully.

        Sets status to COMPLETED and updates final byte count.

        Args:
            url: The URL that was downloaded
            total_bytes: Final size in bytes
        """
        async with self._lock:
            if url not in self._downloads:
                self._downloads[url] = DownloadInfo(url=url)

            self._downloads[url].status = DownloadStatus.COMPLETED
            self._downloads[url].bytes_downloaded = total_bytes
            self._downloads[url].total_bytes = total_bytes

    async def track_failed(self, url: str, error: Exception) -> None:
        """Record that a download failed.

        Sets status to FAILED and stores error message.

        Args:
            url: The URL that failed
            error: The exception that occurred
        """
        async with self._lock:
            if url not in self._downloads:
                self._downloads[url] = DownloadInfo(url=url)

            self._downloads[url].status = DownloadStatus.FAILED
            self._downloads[url].error = str(error)

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
