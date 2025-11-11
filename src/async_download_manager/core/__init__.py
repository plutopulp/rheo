"""Core functionality for async download manager."""

from .base_emitter import BaseEmitter
from .base_tracker import BaseTracker
from .event_emitter import EventEmitter
from .events import (
    DownloadCompletedEvent,
    DownloadEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadStartedEvent,
    WorkerCompletedEvent,
    WorkerEvent,
    WorkerFailedEvent,
    WorkerProgressEvent,
    WorkerStartedEvent,
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
from .null_emitter import NullEmitter
from .null_tracker import NullTracker
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
    "EventEmitter",
    # Base Classes
    "BaseTracker",
    "BaseEmitter",
    # Null Implementations
    "NullTracker",
    "NullEmitter",
    # Models
    "FileConfig",
    "DownloadInfo",
    "DownloadStats",
    "DownloadStatus",
    # Tracker Events
    "DownloadEvent",
    "DownloadQueuedEvent",
    "DownloadStartedEvent",
    "DownloadProgressEvent",
    "DownloadCompletedEvent",
    "DownloadFailedEvent",
    # Worker Events
    "WorkerEvent",
    "WorkerStartedEvent",
    "WorkerProgressEvent",
    "WorkerCompletedEvent",
    "WorkerFailedEvent",
]
