"""Null object implementation of tracker."""

from ..domain.downloads import DownloadInfo
from ..domain.hash_validation import ValidationResult
from .base import BaseTracker


class NullTracker(BaseTracker):
    """Null object implementation of tracker that does nothing.

    Use when tracking is not needed but a tracker interface is required.
    """

    def get_download_info(self, download_id: str) -> DownloadInfo | None:
        """No-op: always returns None."""
        return None

    async def _track_queued(
        self, download_id: str, url: str, priority: int = 1
    ) -> None:
        pass

    async def _track_started(
        self, download_id: str, url: str, total_bytes: int | None = None
    ) -> None:
        pass

    async def _track_progress(
        self,
        download_id: str,
        url: str,
        bytes_downloaded: int,
        total_bytes: int | None = None,
    ) -> None:
        pass

    async def _track_completed(
        self,
        download_id: str,
        url: str,
        total_bytes: int = 0,
        destination_path: str | None = None,
        validation: ValidationResult | None = None,
    ) -> None:
        pass

    async def _track_speed_update(
        self,
        download_id: str,
        current_speed_bps: float,
        average_speed_bps: float,
        eta_seconds: float | None,
        elapsed_seconds: float,
    ) -> None:
        """No-op speed tracking."""
        pass

    async def _track_failed(
        self,
        download_id: str,
        url: str,
        error: Exception,
        validation: ValidationResult | None = None,
    ) -> None:
        pass

    async def _track_skipped(
        self,
        download_id: str,
        url: str,
        reason: str,
        destination_path: str | None = None,
    ) -> None:
        pass

    async def _track_cancelled(self, download_id: str, url: str) -> None:
        pass
