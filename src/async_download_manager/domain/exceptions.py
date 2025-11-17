"""Custom exceptions for the async download manager."""

from pathlib import Path


class DownloadManagerError(Exception):
    """Base exception for DownloadManager errors."""

    pass


class ManagerNotInitializedError(DownloadManagerError):
    """Raised when DownloadManager is accessed before proper initialization.

    This typically occurs when trying to access manager properties without
    using it as a context manager or providing required dependencies.
    """

    pass


class DownloadError(DownloadManagerError):
    """Base exception for download operation errors."""

    pass


class WorkerError(DownloadManagerError):
    """Base exception for worker-related errors."""

    pass


class QueueError(DownloadManagerError):
    """Base exception for queue-related errors."""

    pass


class ProcessQueueError(QueueError):
    """Exception for errors in processing the queue."""

    pass


class ValidationError(DownloadManagerError):
    """Raised when configuration or input validation fails.

    This exception is raised when validating FileConfig or other
    configuration objects with invalid data.
    """

    pass


class RetryError(DownloadManagerError):
    """Raised when retry logic encounters an unexpected state.

    This exception indicates a programming error in the retry handler,
    such as completing the retry loop without returning or raising.
    """

    pass


class FileValidationError(DownloadError):
    """Base exception for file validation failures."""

    pass


class FileAccessError(FileValidationError):
    """Raised when files cannot be accessed for validation."""

    pass


class HashMismatchError(FileValidationError):
    """Raised when calculated hash does not match expected value."""

    def __init__(
        self,
        *,
        expected_hash: str,
        actual_hash: str | None,
        file_path: Path,
    ) -> None:
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        self.file_path = file_path
        message = (
            f"Hash mismatch for {file_path}: expected {expected_hash[:16]}..., "
            f"got {actual_hash[:16] if actual_hash else 'unknown'}..."
        )
        super().__init__(message)
