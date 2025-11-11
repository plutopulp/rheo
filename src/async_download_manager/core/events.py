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


# Worker Events - emitted by DownloadWorker during download lifecycle


@dataclass
class WorkerEvent:
    """Base class for worker lifecycle events.

    Worker events represent the actual download operation state,
    while tracker events represent the overall tracking state.
    """

    url: str
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = "worker.base"


@dataclass
class WorkerStartedEvent(WorkerEvent):
    """Emitted when worker begins downloading a file.

    This event is fired after the HTTP connection is established
    and download begins.
    """

    event_type: str = "worker.started"
    total_bytes: int | None = None


@dataclass
class WorkerProgressEvent(WorkerEvent):
    """Emitted when worker downloads a chunk of data.

    This event is fired after each chunk is received from the server,
    allowing for real-time progress tracking.
    """

    event_type: str = "worker.progress"
    chunk_size: int = 0
    bytes_downloaded: int = 0  # Cumulative bytes downloaded so far
    total_bytes: int | None = None


@dataclass
class WorkerCompletedEvent(WorkerEvent):
    """Emitted when worker successfully completes a download.

    This event is fired after the entire file has been downloaded
    and written to disk.
    """

    event_type: str = "worker.completed"
    destination_path: str = ""
    total_bytes: int = 0


@dataclass
class WorkerFailedEvent(WorkerEvent):
    """Emitted when worker download fails.

    This event is fired when any error occurs during the download
    process (network errors, timeouts, disk errors, etc.).
    """

    event_type: str = "worker.failed"
    error_message: str = ""
    error_type: str = ""
