"""Core functionality for async download manager."""

from .events import (
    DownloadCompletedEvent,
    DownloadEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadStartedEvent,
)
from .exceptions import (
    DownloadError,
    DownloadManagerError,
    ManagerNotInitializedError,
    ProcessQueueError,
    QueueError,
    WorkerError,
)
from .manager import DownloadManager
from .models import DownloadInfo, DownloadStats, DownloadStatus, FileConfig
from .queue import PriorityDownloadQueue
from .tracker import DownloadTracker
from .worker import DownloadWorker

__all__ = [
    # Exceptions
    "DownloadError",
    "DownloadManagerError",
    "ManagerNotInitializedError",
    "ProcessQueueError",
    "QueueError",
    "WorkerError",
    # Classes
    "DownloadManager",
    "DownloadWorker",
    "DownloadTracker",
    "PriorityDownloadQueue",
    # Models
    "FileConfig",
    "DownloadInfo",
    "DownloadStats",
    "DownloadStatus",
    # Events
    "DownloadEvent",
    "DownloadQueuedEvent",
    "DownloadStartedEvent",
    "DownloadProgressEvent",
    "DownloadCompletedEvent",
    "DownloadFailedEvent",
]
