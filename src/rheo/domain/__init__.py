"""Domain layer - core business models and exceptions."""

from .cancellation import CancelledFrom, CancelResult
from .downloads import DownloadInfo, DownloadStats, DownloadStatus
from .exceptions import (
    ClientNotInitialisedError,
    DownloadError,
    DownloadManagerError,
    FileAccessError,
    FileExistsError,
    FileValidationError,
    HashMismatchError,
    HttpClientError,
    InfrastructureError,
    ManagerNotInitialisedError,
    ProcessQueueError,
    QueueError,
    RetryError,
    RheoError,
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
    # Cancellation Models
    "CancelResult",
    "CancelledFrom",
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
    # Exceptions - Base
    "RheoError",
    "DownloadManagerError",
    "InfrastructureError",
    # Exceptions - Infrastructure
    "HttpClientError",
    "ClientNotInitialisedError",
    # Exceptions - Download Manager
    "DownloadError",
    "ManagerNotInitialisedError",
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
