"""Event data models."""

from .base import BaseEvent
from .download import (
    DownloadCompletedEvent,
    DownloadEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadRetryingEvent,
    DownloadStartedEvent,
)
from .error_info import ErrorInfo

__all__ = [
    "BaseEvent",
    "ErrorInfo",
    "DownloadEvent",
    "DownloadStartedEvent",
    "DownloadProgressEvent",
    "DownloadCompletedEvent",
    "DownloadFailedEvent",
    "DownloadRetryingEvent",
]
