"""Null object implementation of tracker."""

from .base import BaseTracker


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

    async def track_speed_update(
        self,
        url: str,
        current_speed_bps: float,
        average_speed_bps: float,
        eta_seconds: float | None,
        elapsed_seconds: float,
    ) -> None:
        """No-op speed tracking."""
        pass

    async def track_failed(self, url: str, error: Exception) -> None:
        pass

    async def track_validation_started(self, url: str, algorithm: str) -> None:
        pass

    async def track_validation_completed(
        self, url: str, algorithm: str, calculated_hash: str
    ) -> None:
        pass

    async def track_validation_failed(
        self,
        url: str,
        algorithm: str,
        expected_hash: str,
        actual_hash: str | None,
        error_message: str,
    ) -> None:
        pass
