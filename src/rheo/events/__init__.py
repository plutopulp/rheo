"""Event infrastructure - event emitter and event types."""

from rheo.domain.cancellation import CancelledFrom
from rheo.domain.hash_validation import ValidationResult

from .base import BaseEmitter
from .emitter import EventEmitter
from .models import (
    BaseEvent,
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
    ErrorInfo,
    EventHandler,
    EventType,
    Handler,
)
from .null import NullEmitter
from .subscription import Subscription

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
    "EventHandler",
    "EventType",
    "Handler",
    "NullEmitter",
    "Subscription",
    # Download Events (from models/)
    "DownloadEvent",
    "DownloadEventType",
    "DownloadQueuedEvent",
    "DownloadSkippedEvent",
    "DownloadCancelledEvent",
    "DownloadStartedEvent",
    "DownloadProgressEvent",
    "DownloadCompletedEvent",
    "DownloadFailedEvent",
    "DownloadRetryingEvent",
    "DownloadValidatingEvent",
    "CancelledFrom",
    "ValidationResult",
    # Worker validation events (will be renamed in Issue #7)
    "WorkerValidationStartedEvent",
    "WorkerValidationCompletedEvent",
    "WorkerValidationFailedEvent",
]
