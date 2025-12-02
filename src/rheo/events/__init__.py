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
    "DownloadStartedEvent",
    "DownloadProgressEvent",
    "DownloadCompletedEvent",
    "DownloadFailedEvent",
    "DownloadRetryingEvent",
    # Worker validation events (will be renamed in Issue #7)
    "WorkerValidationStartedEvent",
    "WorkerValidationCompletedEvent",
    "WorkerValidationFailedEvent",
]
