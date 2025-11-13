"""Domain layer - core business models and exceptions."""

from .downloads import DownloadInfo, DownloadStats, DownloadStatus
from .exceptions import (
    DownloadError,
    DownloadManagerError,
    ManagerNotInitializedError,
    ProcessQueueError,
    QueueError,
    RetryError,
    ValidationError,
    WorkerError,
)
from .file_config import FileConfig
from .retry import ErrorCategory, RetryConfig, RetryPolicy

__all__ = [
    # Download Models
    "FileConfig",
    "DownloadInfo",
    "DownloadStatus",
    "DownloadStats",
    # Retry Models
    "ErrorCategory",
    "RetryConfig",
    "RetryPolicy",
    # Exceptions
    "DownloadError",
    "DownloadManagerError",
    "ManagerNotInitializedError",
    "ProcessQueueError",
    "QueueError",
    "RetryError",
    "ValidationError",
    "WorkerError",
]
