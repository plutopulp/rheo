"""Core domain models for download operations."""

from enum import Enum

from pydantic import BaseModel, Field


class DownloadStatus(Enum):
    """Download lifecycle states.

    Flow: QUEUED -> PENDING -> IN_PROGRESS -> (COMPLETED | FAILED)
    """

    QUEUED = "queued"  # In priority queue
    PENDING = "pending"  # Worker assigned, preparing
    IN_PROGRESS = "in_progress"  # Actively downloading
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"  # Error occurred


class DownloadInfo(BaseModel):
    """File download state container.

    Contains all information about a download: URL, status, progress, and errors.
    For completed downloads, includes final average speed for historical analysis.
    """

    url: str = Field(description="URL of the file being downloaded")
    status: DownloadStatus = Field(
        default=DownloadStatus.PENDING,
        description="Current status of the download",
    )
    bytes_downloaded: int = Field(
        default=0,
        ge=0,
        description="Bytes downloaded so far",
    )
    total_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Total file size in bytes if known",
    )
    error: str | None = Field(
        default=None,
        description="Error message if download failed",
    )
    average_speed_bps: float | None = Field(
        default=None,
        ge=0.0,
        description="Average download speed in bytes/second (set at completion)",
    )

    def get_progress(self) -> float:
        """Calculate progress as fraction (0.0 to 1.0)."""
        if self.total_bytes is None or self.total_bytes == 0:
            return 0.0
        return min(self.bytes_downloaded / self.total_bytes, 1.0)  # Cap at 1.0

    def is_terminal(self) -> bool:
        """Check if download is in a terminal state."""
        return self.status in (DownloadStatus.COMPLETED, DownloadStatus.FAILED)


class DownloadStats(BaseModel):
    """Aggregate statistics about all downloads."""

    total: int = Field(ge=0, description="Total number of downloads tracked")
    queued: int = Field(ge=0, description="Number of downloads in queue")
    in_progress: int = Field(ge=0, description="Number of downloads currently active")
    completed: int = Field(
        ge=0, description="Number of successfully completed downloads"
    )
    failed: int = Field(ge=0, description="Number of failed downloads")
    completed_bytes: int = Field(
        ge=0,
        description="Total bytes successfully downloaded",
    )
