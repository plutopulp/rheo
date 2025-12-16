"""Download lifecycle events with user-centric naming."""

import typing as t
from enum import StrEnum

from pydantic import Field, computed_field

from rheo.domain.cancellation import CancelledFrom
from rheo.domain.hash_validation import HashAlgorithm, ValidationResult
from rheo.domain.speed import SpeedMetrics

from .base import BaseEvent
from .error_info import ErrorInfo


class DownloadEventType(StrEnum):
    """Typed event names for download lifecycle events.

    Use with manager.on() for autocomplete:
        manager.on(DownloadEventType.COMPLETED, handler)
    """

    QUEUED = "download.queued"
    STARTED = "download.started"
    PROGRESS = "download.progress"
    COMPLETED = "download.completed"
    FAILED = "download.failed"
    SKIPPED = "download.skipped"
    CANCELLED = "download.cancelled"
    RETRYING = "download.retrying"
    VALIDATING = "download.validating"


class DownloadEvent(BaseEvent):
    """Base class for all download lifecycle events."""

    download_id: str = Field(description="Unique identifier for this download")
    url: str = Field(description="The URL being downloaded")


class DownloadQueuedEvent(DownloadEvent):
    """Emitted when download is added to queue."""

    event_type: str = Field(default="download.queued")
    priority: int = Field(ge=1, description="Download priority (higher = more urgent)")


class DownloadStartedEvent(DownloadEvent):
    """Emitted when download begins (HTTP request started)."""

    event_type: str = Field(default="download.started")
    total_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Total file size if known from Content-Length",
    )


class DownloadProgressEvent(DownloadEvent):
    """Emitted when data chunk received.

    Speed metrics are optional - None when speed tracking is disabled.
    """

    event_type: str = Field(default="download.progress")
    chunk_size: int = Field(default=0, ge=0, description="Size of last received chunk")
    bytes_downloaded: int = Field(
        default=0, ge=0, description="Cumulative bytes downloaded so far"
    )
    total_bytes: int | None = Field(
        default=None, ge=0, description="Total file size if known from Content-Length"
    )
    # Optional speed metrics (None when speed tracking disabled)
    speed: SpeedMetrics | None = Field(
        default=None,
        description="Speed metrics snapshot, None if speed tracking disabled",
    )

    @computed_field  # type: ignore [prop-decorator]
    @property
    def progress_percent(self) -> float | None:
        """Progress as percentage (0-100), None if total unknown."""
        if self.total_bytes and self.total_bytes > 0:
            return (self.bytes_downloaded / self.total_bytes) * 100
        return None


class DownloadCompletedEvent(DownloadEvent):
    """Emitted when download finishes successfully."""

    event_type: str = Field(default="download.completed")
    destination_path: str = Field(default="", description="Path where file was saved")
    total_bytes: int = Field(default=0, ge=0, description="Total bytes downloaded")
    elapsed_seconds: float = Field(
        default=0.0, ge=0, description="Total download duration in seconds"
    )
    average_speed_bps: float = Field(
        default=0.0, ge=0, description="Final average speed in bytes/second"
    )
    validation: ValidationResult | None = Field(
        default=None,
        description="Validation result when hash verification is configured",
    )


class DownloadFailedEvent(DownloadEvent):
    """Emitted when download fails.

    For validation failures, check validation field:
    - validation.expected_hash vs validation.calculated_hash shows mismatch
    - error.exc_type will be "HashMismatchError"
    """

    event_type: str = Field(default="download.failed")
    error: ErrorInfo = Field(description="Structured error information")
    validation: ValidationResult | None = Field(
        default=None,
        description="Validation result when hash validation was attempted",
    )


class DownloadSkippedEvent(DownloadEvent):
    """Emitted when download is skipped (e.g., file already exists)."""

    event_type: str = Field(default="download.skipped")
    reason: str = Field(description="Why download was skipped (e.g., 'file_exists')")
    destination_path: str | None = Field(
        default=None, description="Path that was skipped"
    )


class DownloadCancelledEvent(DownloadEvent):
    """Emitted when download is cancelled by user request.

    Provides context about what state the download was in when cancelled.
    """

    event_type: str = Field(default="download.cancelled")
    cancelled_from: CancelledFrom = Field(
        description="State the download was in when cancelled (queued or in_progress)"
    )


class DownloadRetryingEvent(DownloadEvent):
    """Emitted when about to retry a failed download.

    Uses retry terminology (not attempt) for clarity:
    - 1st attempt fails → retry=1 (about to make 1st retry)
    - 2nd attempt fails → retry=2 (about to make 2nd retry)
    """

    event_type: str = Field(default="download.retrying")
    retry: int = Field(
        ge=1, description="Retry number (1 = first retry, 2 = second retry)"
    )
    max_retries: int = Field(ge=1, description="Maximum retries configured")
    delay_seconds: float = Field(
        default=0.0, ge=0, description="Delay before this retry in seconds"
    )
    error: ErrorInfo = Field(description="Error that triggered this retry")


class DownloadValidatingEvent(DownloadEvent):
    """Emitted when hash validation starts."""

    event_type: str = Field(default="download.validating")
    algorithm: HashAlgorithm = Field(
        description="Hash algorithm used for validation",
    )


# Generic event handler type
# Usage: def my_handler(event: DownloadCompletedEvent) -> None: ...
E = t.TypeVar("E")
Handler = t.Callable[[E], t.Union[None, t.Awaitable[None]]]

# Type aliases for event subscription (centralised for maintainability)
EventType = DownloadEventType | str

# EventHandler uses Any to allow handlers with specific event types (e.g.,
# DownloadCompletedEvent) without requiring @overload signatures on manager.on().
# Users should type-hint their handler parameters for autocomplete on event fields.
EventHandler = Handler[t.Any]
