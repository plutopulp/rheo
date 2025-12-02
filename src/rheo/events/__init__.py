"""Event infrastructure - event emitter and event types."""

from .base import BaseEmitter
from .emitter import EventEmitter
from .models import BaseEvent, ErrorInfo
from .null import NullEmitter
from .tracker_events import (
    DownloadCompletedEvent,
    DownloadEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadStartedEvent,
    DownloadValidationCompletedEvent,
    DownloadValidationFailedEvent,
    DownloadValidationStartedEvent,
)
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
    # Tracker Events
    "DownloadEvent",
    "DownloadQueuedEvent",
    "DownloadStartedEvent",
    "DownloadProgressEvent",
    "DownloadCompletedEvent",
    "DownloadFailedEvent",
    "DownloadValidationStartedEvent",
    "DownloadValidationCompletedEvent",
    "DownloadValidationFailedEvent",
    # Worker Events
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
