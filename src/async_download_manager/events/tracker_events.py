"""Events emitted by DownloadTracker during lifecycle changes."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DownloadEvent:
    """Base class for all download tracker events.

    All events include a timestamp and the URL being tracked.
    """

    url: str
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = "tracker.base"


@dataclass
class DownloadQueuedEvent(DownloadEvent):
    """Fired when a download is added to the tracker queue."""

    event_type: str = "tracker.queued"
    priority: int = 1


@dataclass
class DownloadStartedEvent(DownloadEvent):
    """Fired when tracker records a download has begun."""

    event_type: str = "tracker.started"
    total_bytes: int | None = None


@dataclass
class DownloadProgressEvent(DownloadEvent):
    """Fired periodically when tracker records download progress."""

    event_type: str = "tracker.progress"
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
    """Fired when tracker records a download completed successfully."""

    event_type: str = "tracker.completed"
    destination_path: str = ""
    total_bytes: int = 0


@dataclass
class DownloadFailedEvent(DownloadEvent):
    """Fired when tracker records a download failed."""

    event_type: str = "tracker.failed"
    error_message: str = ""
    error_type: str = ""
