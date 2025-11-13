"""Event infrastructure - event emitter and event types."""

from .base import BaseEmitter
from .emitter import EventEmitter
from .null import NullEmitter
from .tracker_events import (
    DownloadCompletedEvent,
    DownloadEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadStartedEvent,
)
from .worker_events import (
    WorkerCompletedEvent,
    WorkerEvent,
    WorkerFailedEvent,
    WorkerProgressEvent,
    WorkerRetryEvent,
    WorkerStartedEvent,
)

__all__ = [
    # Base and implementations
    "BaseEmitter",
    "EventEmitter",
    "NullEmitter",
    # Tracker Events
    "DownloadEvent",
    "DownloadQueuedEvent",
    "DownloadStartedEvent",
    "DownloadProgressEvent",
    "DownloadCompletedEvent",
    "DownloadFailedEvent",
    # Worker Events
    "WorkerEvent",
    "WorkerStartedEvent",
    "WorkerProgressEvent",
    "WorkerCompletedEvent",
    "WorkerFailedEvent",
    "WorkerRetryEvent",
]
