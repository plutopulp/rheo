"""Download operations - manager, worker, queue, and retry."""

from ..domain.exceptions import FileAccessError, FileValidationError, HashMismatchError
from .manager import DownloadManager
from .queue import PriorityDownloadQueue
from .retry import BaseRetryHandler, ErrorCategoriser, NullRetryHandler, RetryHandler
from .validation import BaseFileValidator, FileValidator, NullFileValidator
from .worker import DownloadWorker

__all__ = [
    # Core downloads
    "DownloadManager",
    "DownloadWorker",
    "PriorityDownloadQueue",
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
