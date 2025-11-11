"""Download event models for tracking lifecycle changes."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DownloadEvent:
    """Base class for all download events.

    All events include a timestamp and the URL being tracked.
    """

    url: str
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = "base"


@dataclass
class DownloadQueuedEvent(DownloadEvent):
    """Fired when a download is added to the queue."""

    event_type: str = "queued"
    priority: int = 1


@dataclass
class DownloadStartedEvent(DownloadEvent):
    """Fired when a download begins."""

    event_type: str = "started"
    total_bytes: int | None = None


@dataclass
class DownloadProgressEvent(DownloadEvent):
    """Fired periodically during download to report progress."""

    event_type: str = "progress"
    bytes_downloaded: int = 0
    total_bytes: int | None = None

    @property
    def progress_fraction(self) -> float:
        """Get progress as a fraction (0.0 to 1.0)."""
        if self.total_bytes is None or self.total_bytes == 0:
            return 0.0
        return min(self.bytes_downloaded / self.total_bytes, 1.0)

    @property
    def progress_percent(self) -> float:
        """Get progress as a percentage (0.0 to 100.0)."""
        return self.progress_fraction * 100.0


@dataclass
class DownloadCompletedEvent(DownloadEvent):
    """Fired when a download completes successfully."""

    event_type: str = "completed"
    destination_path: str = ""
    total_bytes: int = 0


@dataclass
class DownloadFailedEvent(DownloadEvent):
    """Fired when a download fails."""

    event_type: str = "failed"
    error_message: str = ""
    error_type: str = ""
