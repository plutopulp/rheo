"""Event infrastructure - event emitter and event types."""

from rheo.domain.hash_validation import ValidationResult

from .base import BaseEmitter
from .emitter import EventEmitter
from .models import (
    BaseEvent,
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
    ErrorInfo,
)
from .null import NullEmitter

# Worker validation events - will be renamed to download.* in Issue #7
from .worker_events import (
    WorkerValidationCompletedEvent,
    WorkerValidationFailedEvent,
    WorkerValidationStartedEvent,
)

__all__ = [
    # Base and implementations
    "BaseEmitter",
    "BaseEvent",
    "ErrorInfo",
    "EventEmitter",
    "NullEmitter",
    # Download Events (from models/)
    "DownloadEvent",
    "DownloadQueuedEvent",
    "DownloadSkippedEvent",
    "DownloadCancelledEvent",
    "DownloadStartedEvent",
    "DownloadProgressEvent",
    "DownloadCompletedEvent",
    "DownloadFailedEvent",
    "DownloadRetryingEvent",
    "DownloadValidatingEvent",
    "ValidationResult",
    # Worker validation events (will be renamed in Issue #7)
    "WorkerValidationStartedEvent",
    "WorkerValidationCompletedEvent",
    "WorkerValidationFailedEvent",
]
