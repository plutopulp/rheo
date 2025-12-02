"""Event infrastructure - event emitter and event types."""

from .base import BaseEmitter
from .emitter import EventEmitter
from .models import (
    BaseEvent,
    DownloadCompletedEvent,
    DownloadEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadRetryingEvent,
    DownloadStartedEvent,
    ErrorInfo,
)
from .null import NullEmitter

# Legacy tracker events - will be removed in future (Issue #6)
from .tracker_events import (
    DownloadQueuedEvent,
    DownloadValidationCompletedEvent,
    DownloadValidationFailedEvent,
    DownloadValidationStartedEvent,
)

# Legacy worker events - keeping validation events for now (Issue #7)
from .worker_events import (
    WorkerCompletedEvent,
    WorkerEvent,
    WorkerFailedEvent,
    WorkerProgressEvent,
    WorkerRetryEvent,
    WorkerSpeedUpdatedEvent,
    WorkerStartedEvent,
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
    # Download Events (new - from models/)
    "DownloadEvent",
    "DownloadStartedEvent",
    "DownloadProgressEvent",
    "DownloadCompletedEvent",
    "DownloadFailedEvent",
    "DownloadRetryingEvent",
    # Legacy tracker events - to be removed (Issue #6)
    "DownloadQueuedEvent",
    "DownloadValidationStartedEvent",
    "DownloadValidationCompletedEvent",
    "DownloadValidationFailedEvent",
    # Legacy worker events (Issue #7 - validation events remain)
    "WorkerEvent",
    "WorkerStartedEvent",
    "WorkerProgressEvent",
    "WorkerCompletedEvent",
    "WorkerFailedEvent",
    "WorkerRetryEvent",
    "WorkerSpeedUpdatedEvent",
    "WorkerValidationStartedEvent",
    "WorkerValidationCompletedEvent",
    "WorkerValidationFailedEvent",
]
