"""Download operations - manager, worker, queue, and retry."""

from ..domain.exceptions import FileAccessError, FileValidationError, HashMismatchError
from .base_retry import BaseRetryHandler
from .base_validator import BaseFileValidator
from .error_categoriser import ErrorCategoriser
from .manager import DownloadManager
from .null_retry import NullRetryHandler
from .null_validator import NullFileValidator
from .queue import PriorityDownloadQueue
from .retry_handler import RetryHandler
from .validation import FileValidator
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
