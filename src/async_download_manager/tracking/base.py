"""Abstract base class for download trackers."""

from abc import ABC, abstractmethod


class BaseTracker(ABC):
    """Abstract base class for download trackers."""

    @abstractmethod
    async def track_queued(self, url: str, priority: int = 1) -> None:
        """Track when a download is queued."""
        pass

    @abstractmethod
    async def track_started(self, url: str, total_bytes: int | None = None) -> None:
        """Track when a download starts."""
        pass

    @abstractmethod
    async def track_progress(
        self, url: str, bytes_downloaded: int, total_bytes: int | None = None
    ) -> None:
        """Track download progress."""
        pass

    @abstractmethod
    async def track_completed(
        self, url: str, total_bytes: int = 0, destination_path: str = ""
    ) -> None:
        """Track when a download completes."""
        pass

    @abstractmethod
    async def track_failed(self, url: str, error: Exception) -> None:
        """Track when a download fails."""
        pass

    @abstractmethod
    async def track_speed_update(
        self,
        url: str,
        current_speed_bps: float,
        average_speed_bps: float,
        eta_seconds: float | None,
        elapsed_seconds: float,
    ) -> None:
        """Track when a download speed is updated."""
        pass
