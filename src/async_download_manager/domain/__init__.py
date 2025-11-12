"""Domain layer - core business models and exceptions."""

from .downloads import DownloadInfo, DownloadStats, DownloadStatus
from .exceptions import (
    DownloadError,
    DownloadManagerError,
    ManagerNotInitializedError,
    ProcessQueueError,
    QueueError,
    ValidationError,
    WorkerError,
)
from .file_config import FileConfig

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
    "ValidationError",
    "WorkerError",
]
