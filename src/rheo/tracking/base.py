"""Abstract base class for download trackers.

Trackers are observers that store download state. They do NOT emit events.
Events are emitted by the worker using the download.* namespace.
Subscribe to events via the manager or worker emitter directly.
"""

from abc import ABC, abstractmethod

from ..domain.downloads import DownloadInfo
from ..domain.hash_validation import ValidationResult


class BaseTracker(ABC):
    """Abstract base class for download trackers.

    Trackers store state and provide query methods. They are observers that
    receive state updates from the pool's event wiring. They do not emit events.

    For event subscription, use the manager or worker emitter:
        manager.worker.emitter.on("download.progress", handler)
    """

    @abstractmethod
    def get_download_info(self, download_id: str) -> DownloadInfo | None:
        """Get current state of a download.

        Args:
            download_id: The download ID to query

        Returns:
            DownloadInfo if found, None otherwise
        """
        pass

    @abstractmethod
    async def track_queued(self, download_id: str, url: str, priority: int = 1) -> None:
        """Track when a download is queued."""
        pass

    @abstractmethod
    async def track_started(
        self, download_id: str, url: str, total_bytes: int | None = None
    ) -> None:
        """Track when a download starts."""
        pass

    @abstractmethod
    async def track_progress(
        self,
        download_id: str,
        url: str,
        bytes_downloaded: int,
        total_bytes: int | None = None,
    ) -> None:
        """Track download progress."""
        pass

    @abstractmethod
    async def track_completed(
        self,
        download_id: str,
        url: str,
        total_bytes: int = 0,
        destination_path: str = "",
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
        pass

    @abstractmethod
    async def track_failed(
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
        pass

    @abstractmethod
    async def track_speed_update(
        self,
        download_id: str,
        current_speed_bps: float,
        average_speed_bps: float,
        eta_seconds: float | None,
        elapsed_seconds: float,
    ) -> None:
        """Track when a download speed is updated."""
        pass
