"""Core domain models for download operations."""

from dataclasses import dataclass
from enum import Enum


class DownloadStatus(Enum):
    """Download lifecycle states.

    Flow: QUEUED -> PENDING -> IN_PROGRESS -> (COMPLETED | FAILED)
    """

    QUEUED = "queued"  # In priority queue
    PENDING = "pending"  # Worker assigned, preparing
    IN_PROGRESS = "in_progress"  # Actively downloading
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"  # Error occurred


@dataclass
class DownloadInfo:
    """File download state container.

    Contains all information about a download: URL, status, progress, and errors.
    """

    url: str
    status: DownloadStatus = DownloadStatus.PENDING
    bytes_downloaded: int = 0
    total_bytes: int | None = None
    error: str | None = None

    def get_progress(self) -> float:
        """Calculate progress as fraction (0.0 to 1.0)."""
        if self.total_bytes is None or self.total_bytes == 0:
            return 0.0
        return min(self.bytes_downloaded / self.total_bytes, 1.0)  # Cap at 1.0

    def is_terminal(self) -> bool:
        """Check if download is in a terminal state."""
        return self.status in (DownloadStatus.COMPLETED, DownloadStatus.FAILED)


@dataclass
class DownloadStats:
    """Aggregate statistics about all downloads."""

    total: int
    queued: int
    in_progress: int
    completed: int
    failed: int
    completed_bytes: int
