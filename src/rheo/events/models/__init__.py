"""Event data models."""

from rheo.domain.hash_validation import ValidationResult

from .base import BaseEvent
from .download import (
    DownloadCancelledEvent,
    DownloadCompletedEvent,
    DownloadEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadRetryingEvent,
    DownloadSkippedEvent,
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
    "DownloadSkippedEvent",
    "DownloadCancelledEvent",
    "DownloadRetryingEvent",
    "DownloadValidatingEvent",
    "ValidationResult",
]
