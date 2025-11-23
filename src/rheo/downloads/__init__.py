"""Download operations - manager, worker, queue, and retry."""

from ..domain.exceptions import FileAccessError, FileValidationError, HashMismatchError
from .manager import DownloadManager
from .queue import PriorityDownloadQueue
from .retry import BaseRetryHandler, ErrorCategoriser, NullRetryHandler, RetryHandler
from .validation import BaseFileValidator, FileValidator, NullFileValidator
from .worker import BaseWorker, DownloadWorker, WorkerFactory

__all__ = [
    # Core downloads
    "DownloadManager",
    "DownloadWorker",
    "PriorityDownloadQueue",
    # Worker
    "BaseWorker",
    "WorkerFactory",
    # Retry
    "BaseRetryHandler",
    "RetryHandler",
    "NullRetryHandler",
    "ErrorCategoriser",
    # Validation
    "BaseFileValidator",
    "FileValidator",
    "NullFileValidator",
    "FileValidationError",
    "FileAccessError",
    "HashMismatchError",
]
