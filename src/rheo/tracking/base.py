"""Abstract base class for download trackers.

Trackers are observers that store download state. They do NOT emit events.
Events are emitted by the worker using the download.* namespace.
Subscribe to events via the manager or worker emitter directly.
"""

from abc import ABC, abstractmethod

from ..domain.downloads import DownloadInfo, DownloadStats
from ..domain.hash_validation import ValidationResult
from ..domain.speed import SpeedMetrics


class BaseTracker(ABC):
    """Abstract base class for download trackers.

    Trackers store state and provide query methods. They are observers that
    receive state updates from the pool's event wiring. They do not emit events.

    For event subscription, use the manager:
        manager.on("download.progress", handler)
    """

    @abstractmethod
    def get_download_info(self, download_id: str) -> DownloadInfo | None:
        """Get current state of a download.

        Args:
            download_id: The download ID to query

        Returns:
            DownloadInfo if found, None otherwise
        """
        ...

    @abstractmethod
    def get_stats(self) -> DownloadStats:
        """Get aggregate download statistics."""
        ...

    @abstractmethod
    async def _track_queued(
        self, download_id: str, url: str, priority: int = 1
    ) -> None:
        """Track when a download is queued."""
        ...

    @abstractmethod
    async def _track_started(
        self, download_id: str, url: str, total_bytes: int | None = None
    ) -> None:
        """Track when a download starts."""
        ...

    @abstractmethod
    async def _track_progress(
        self,
        download_id: str,
        url: str,
        bytes_downloaded: int,
        total_bytes: int | None = None,
        speed: SpeedMetrics | None = None,
    ) -> None:
        """Track download progress with optional speed metrics."""
        ...

    @abstractmethod
    async def _track_completed(
        self,
        download_id: str,
        url: str,
        total_bytes: int = 0,
        destination_path: str | None = None,
        validation: ValidationResult | None = None,
    ) -> None:
        """Track when a download completes.

        Args:
            download_id: Unique identifier for this download
            url: The URL that was downloaded
            total_bytes: Final file size in bytes
            destination_path: Where the file was saved
            validation: Optional validation result from hash verification
        """
        ...

    @abstractmethod
    async def _track_failed(
        self,
        download_id: str,
        url: str,
        error: Exception,
        validation: ValidationResult | None = None,
    ) -> None:
        """Track when a download fails.

        Args:
            download_id: Unique identifier for this download
            url: The URL that failed
            error: The exception that occurred
            validation: Optional validation result when failure is hash mismatch
        """
        ...

    @abstractmethod
    async def _track_skipped(
        self,
        download_id: str,
        url: str,
        reason: str,
        destination_path: str | None = None,
    ) -> None:
        """Track when a download is skipped."""
        ...

    @abstractmethod
    async def _track_cancelled(self, download_id: str, url: str) -> None:
        """Track when a download is cancelled."""
        ...
