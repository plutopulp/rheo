"""Validation events emitted by DownloadWorker.

These events cover hash validation lifecycle. They will be renamed to
download.validation.* in a future release (Issue #7).

For download lifecycle events (started, progress, completed, failed),
see events/models/download.py which uses the download.* namespace.
"""

from pydantic import Field

from .models.base import BaseEvent


class WorkerValidationEvent(BaseEvent):
    """Base class for worker validation events."""

    download_id: str = Field(description="Unique identifier for this download")
    url: str = Field(description="The URL being downloaded")


class WorkerValidationStartedEvent(WorkerValidationEvent):
    """Emitted when hash validation starts."""

    event_type: str = Field(default="worker.validation_started")
    # TODO: Use HashAlgorithm enum from domain
    algorithm: str = Field(default="", description="Hash algorithm used")
    file_path: str = Field(default="", description="Path to file being validated")
    file_size_bytes: int | None = Field(
        default=None, ge=0, description="File size in bytes"
    )


class WorkerValidationCompletedEvent(WorkerValidationEvent):
    """Emitted when hash validation succeeds."""

    event_type: str = Field(default="worker.validation_completed")
    # TODO: Use HashAlgorithm enum from domain
    algorithm: str = Field(default="", description="Hash algorithm used")
    calculated_hash: str = Field(default="", description="Computed hash value")
    duration_ms: float = Field(
        default=0.0, ge=0, description="Validation duration in ms"
    )
    file_path: str = Field(default="", description="Path to validated file")


class WorkerValidationFailedEvent(WorkerValidationEvent):
    """Emitted when hash validation fails.

    TODO: Replace error_message with ErrorInfo model.
    """

    event_type: str = Field(default="worker.validation_failed")
    # TODO: Use HashAlgorithm enum from domain
    algorithm: str = Field(default="", description="Hash algorithm used")
    expected_hash: str = Field(default="", description="Expected hash value")
    actual_hash: str | None = Field(default=None, description="Actual computed hash")
    error_message: str = Field(default="", description="Error description")
    file_path: str = Field(
        default="", description="Path to file that failed validation"
    )
