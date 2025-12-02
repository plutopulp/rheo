"""Event data models."""

from .base import BaseEvent
from .download import (
    DownloadCompletedEvent,
    DownloadEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadRetryingEvent,
    DownloadStartedEvent,
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
]
