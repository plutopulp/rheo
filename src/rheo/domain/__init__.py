"""Domain layer - core business models and exceptions."""

from .downloads import DownloadInfo, DownloadStats, DownloadStatus
from .exceptions import (
    DownloadError,
    DownloadManagerError,
    FileAccessError,
    FileExistsError,
    FileValidationError,
    HashMismatchError,
    ManagerNotInitializedError,
    ProcessQueueError,
    QueueError,
    RetryError,
    ValidationError,
    WorkerError,
)
from .file_config import FileConfig, FileExistsStrategy
from .hash_validation import (
    HashAlgorithm,
    HashConfig,
    ValidationResult,
)
from .retry import ErrorCategory, RetryConfig, RetryPolicy

__all__ = [
    # Download Models
    "FileConfig",
    "FileExistsStrategy",
    "DownloadInfo",
    "DownloadStatus",
    "DownloadStats",
    "HashAlgorithm",
    "HashConfig",
    "ValidationResult",
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
    "FileValidationError",
    "FileAccessError",
    "FileExistsError",
    "HashMismatchError",
]
