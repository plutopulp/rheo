"""Custom exceptions for the async download manager."""


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
