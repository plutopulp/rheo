"""Events emitted by DownloadWorker during download operations."""

from dataclasses import dataclass, field
from datetime import datetime


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
