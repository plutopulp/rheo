"""Domain layer - core business models and exceptions."""

from .downloads import DownloadInfo, DownloadStats, DownloadStatus, FileConfig
from .exceptions import (
    DownloadError,
    DownloadManagerError,
    ManagerNotInitializedError,
    ProcessQueueError,
    QueueError,
    WorkerError,
)

__all__ = [
    # Download Models
    "FileConfig",
    "DownloadInfo",
    "DownloadStatus",
    "DownloadStats",
    # Exceptions
    "DownloadError",
    "DownloadManagerError",
    "ManagerNotInitializedError",
    "ProcessQueueError",
    "QueueError",
    "WorkerError",
]
