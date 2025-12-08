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


class PendingDownloadsError(DownloadManagerError):
    """Raised when exiting DownloadManager with unprocessed downloads."""

    def __init__(self, pending_count: int) -> None:
        self.pending_count = pending_count
        message = (
            f"Exited DownloadManager with {pending_count} pending download(s). "
            "These have been cancelled. To avoid this, call "
            "await manager.wait_until_complete() before exiting, "
            "or await manager.close() to cancel explicitly."
        )
        super().__init__(message)


class DownloadError(DownloadManagerError):
    """Base exception for download operation errors."""

    pass


class WorkerError(DownloadManagerError):
    """Base exception for worker-related errors."""

    pass


class WorkerPoolError(DownloadManagerError):
    """Base exception for worker pool errors."""

    pass


class WorkerPoolAlreadyStartedError(WorkerPoolError):
    """Raised when attempting to start an already-running worker pool.

    This prevents pool state corruption from multiple start() calls.
    """

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


class FileExistsError(DownloadError):
    """Raised when destination file exists and strategy is ERROR."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"File already exists: {path}")


class HashMismatchError(FileValidationError):
    """Raised when calculated hash does not match expected value."""

    def __init__(
        self,
        *,
        expected_hash: str,
        calculated_hash: str | None,
        file_path: Path,
    ) -> None:
        self.expected_hash = expected_hash
        self.calculated_hash = calculated_hash
        self.file_path = file_path
        message = (
            f"Hash mismatch for {file_path}: expected {expected_hash[:16]}..., "
            f"got {calculated_hash[:16] if calculated_hash else 'unknown'}..."
        )
        super().__init__(message)
