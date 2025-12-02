"""Events emitted by DownloadWorker during download operations."""

from pydantic import Field

from .base_event import BaseEvent


class WorkerEvent(BaseEvent):
    """Base class for worker lifecycle events.

    Worker events represent the actual download operation state,
    while tracker events represent the overall tracking state.

    All worker events include download_id to identify which download
    task the event relates to.
    """

    download_id: str = Field(description="Unique identifier for this download")
    url: str = Field(description="The URL being downloaded")
    event_type: str = Field(default="worker.base", description="Event type identifier")


class WorkerStartedEvent(WorkerEvent):
    """Emitted when worker begins downloading a file."""

    event_type: str = Field(default="worker.started")
    total_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Total file size if known from Content-Length",
    )


class WorkerProgressEvent(WorkerEvent):
    """Emitted when worker downloads a chunk of data."""

    event_type: str = Field(default="worker.progress")
    chunk_size: int = Field(default=0, ge=0, description="Size of last received chunk")
    bytes_downloaded: int = Field(
        default=0, ge=0, description="Cumulative bytes downloaded so far"
    )
    total_bytes: int | None = Field(
        default=None, ge=0, description="Total file size if known"
    )


class WorkerCompletedEvent(WorkerEvent):
    """Emitted when worker successfully completes a download."""

    event_type: str = Field(default="worker.completed")
    destination_path: str = Field(default="", description="Path where file was saved")
    total_bytes: int = Field(default=0, ge=0, description="Total bytes downloaded")


class WorkerFailedEvent(WorkerEvent):
    """Emitted when worker download fails.

    TODO: Replace error_message/error_type with ErrorInfo model
    """

    event_type: str = Field(default="worker.failed")
    error_message: str = Field(default="", description="Error message")
    error_type: str = Field(default="", description="Exception type name")


class WorkerRetryEvent(WorkerEvent):
    """Emitted when a download is being retried.

    TODO: Replace error_message with ErrorInfo model
    """

    event_type: str = Field(default="worker.retry")
    attempt: int = Field(ge=1, description="Current attempt number (1-indexed)")
    max_retries: int = Field(ge=1, description="Maximum retry attempts")
    error_message: str = Field(default="", description="Error that triggered retry")
    retry_delay: float = Field(
        default=1.0, ge=0, description="Delay before retry in seconds"
    )


class WorkerSpeedUpdatedEvent(WorkerEvent):
    """Emitted when download speed metrics are updated."""

    event_type: str = Field(default="worker.speed_updated")
    current_speed_bps: float = Field(
        default=0.0, ge=0, description="Instantaneous speed in bytes/second"
    )
    average_speed_bps: float = Field(
        default=0.0, ge=0, description="Moving average speed in bytes/second"
    )
    eta_seconds: float | None = Field(
        default=None, ge=0, description="Estimated time to completion"
    )
    elapsed_seconds: float = Field(
        default=0.0, ge=0, description="Time elapsed since download started"
    )
    bytes_downloaded: int = Field(
        default=0, ge=0, description="Cumulative bytes downloaded"
    )
    total_bytes: int | None = Field(
        default=None, ge=0, description="Total file size if known"
    )


class WorkerValidationStartedEvent(WorkerEvent):
    """Emitted when hash validation starts."""

    event_type: str = Field(default="worker.validation_started")
    # TODO: Use HashAlgorithm enum from domain
    algorithm: str = Field(default="", description="Hash algorithm used")
    file_path: str = Field(default="", description="Path to file being validated")
    file_size_bytes: int | None = Field(
        default=None, ge=0, description="File size in bytes"
    )


class WorkerValidationCompletedEvent(WorkerEvent):
    """Emitted when hash validation succeeds."""

    event_type: str = Field(default="worker.validation_completed")
    # TODO: Use HashAlgorithm enum from domain
    algorithm: str = Field(default="", description="Hash algorithm used")
    calculated_hash: str = Field(default="", description="Computed hash value")
    duration_ms: float = Field(
        default=0.0, ge=0, description="Validation duration in ms"
    )
    file_path: str = Field(default="", description="Path to validated file")


class WorkerValidationFailedEvent(WorkerEvent):
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
