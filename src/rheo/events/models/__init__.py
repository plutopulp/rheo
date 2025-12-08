"""Event data models."""

from rheo.domain.hash_validation import ValidationResult

from .base import BaseEvent
from .download import (
    DownloadCompletedEvent,
    DownloadEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadRetryingEvent,
    DownloadStartedEvent,
    DownloadValidatingEvent,
)
from .error_info import ErrorInfo

__all__ = [
    "BaseEvent",
    "ErrorInfo",
    "DownloadEvent",
    "DownloadQueuedEvent",
    "DownloadStartedEvent",
    "DownloadProgressEvent",
    "DownloadCompletedEvent",
    "DownloadFailedEvent",
    "DownloadRetryingEvent",
    "DownloadValidatingEvent",
    "ValidationResult",
]
