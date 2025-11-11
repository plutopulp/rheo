"""Null object implementation of tracker."""

from .base_tracker import BaseTracker


class NullTracker(BaseTracker):
    """Null object implementation of tracker that does nothing."""

    async def track_queued(self, url: str, priority: int = 1) -> None:
        pass

    async def track_started(self, url: str, total_bytes: int | None = None) -> None:
        pass

    async def track_progress(
        self, url: str, bytes_downloaded: int, total_bytes: int | None = None
    ) -> None:
        pass

    async def track_completed(
        self, url: str, total_bytes: int = 0, destination_path: str = ""
    ) -> None:
        pass

    async def track_failed(self, url: str, error: Exception) -> None:
        pass
