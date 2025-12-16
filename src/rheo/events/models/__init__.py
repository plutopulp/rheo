"""Event data models."""

from rheo.domain.cancellation import CancelledFrom
from rheo.domain.hash_validation import ValidationResult

from .base import BaseEvent
from .download import (
    DownloadCancelledEvent,
    DownloadCompletedEvent,
    DownloadEvent,
    DownloadEventType,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadRetryingEvent,
    DownloadSkippedEvent,
    DownloadStartedEvent,
    DownloadValidatingEvent,
    EventHandler,
    EventType,
    Handler,
)
from .error_info import ErrorInfo

__all__ = [
    "BaseEvent",
    "ErrorInfo",
    "DownloadEvent",
    "DownloadEventType",
    "DownloadQueuedEvent",
    "DownloadStartedEvent",
    "DownloadProgressEvent",
    "DownloadCompletedEvent",
    "DownloadFailedEvent",
    "DownloadSkippedEvent",
    "DownloadCancelledEvent",
    "DownloadRetryingEvent",
    "DownloadValidatingEvent",
    "EventHandler",
    "EventType",
    "Handler",
    "ValidationResult",
    "CancelledFrom",
]
