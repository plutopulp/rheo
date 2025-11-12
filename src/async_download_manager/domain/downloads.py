"""Core domain models for download operations."""

from dataclasses import dataclass
from enum import Enum


@dataclass
class FileConfig:
    """Download specification with URL, priority, and metadata.

    Priority: higher numbers = higher priority (1=low, 5=high)
    Size info enables progress bars; omit if unknown.
    """

    # ========== Required ==========
    url: str

    # ========== Metadata (for UI/logging) ==========
    # The MIME type of the file (optional, for content validation)
    type: str | None = None
    # Human-readable description of the file (optional, for UI/logging)
    description: str | None = None
    # Priority for queue scheduling - higher numbers = higher priority (default: 1)
    priority: int = 1
    # Human-readable size estimate for display (optional)
    size_human: str | None = None
    # Exact size in bytes for progress calculation (optional)
    size_bytes: int | None = None

    # ========== File Management ==========
    # TODO: Implement custom filename override in worker.download()
    filename: str | None = None
    # TODO: Implement subdir support in manager.process_queue()
    destination_subdir: str | None = None

    # ========== Download Behavior ==========
    # TODO: Implement per-file timeout override in worker.download()
    timeout: float | None = None
    # TODO: Implement retry logic in manager or worker
    max_retries: int = 0


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
