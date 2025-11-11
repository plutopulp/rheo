"""Core functionality for async download manager."""

from .exceptions import (
    DownloadError,
    DownloadManagerError,
    ManagerNotInitializedError,
    ProcessQueueError,
    QueueError,
    WorkerError,
)
from .manager import DownloadManager
from .models import DownloadInfo, DownloadStatus, FileConfig
from .queue import PriorityDownloadQueue
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
    "PriorityDownloadQueue",
    # Models
    "FileConfig",
    "DownloadInfo",
    "DownloadStatus",
]
