"""Events emitted by DownloadTracker during lifecycle changes."""

from pydantic import Field, computed_field

from .base_event import BaseEvent


class DownloadEvent(BaseEvent):
    """Base class for all download tracker events.

    All events include the download ID, URL, and timestamp.
    The download_id uniquely identifies which download this event relates to.
    """

    download_id: str = Field(description="Unique identifier for this download")
    url: str = Field(description="The URL being downloaded")
    event_type: str = Field(default="tracker.base", description="Event type identifier")


class DownloadQueuedEvent(DownloadEvent):
    """Fired when a download is added to the tracker queue."""

    event_type: str = Field(default="tracker.queued")
    priority: int = Field(default=1, ge=1, description="Download priority")


class DownloadStartedEvent(DownloadEvent):
    """Fired when tracker records a download has begun."""

    event_type: str = Field(default="tracker.started")
    total_bytes: int | None = Field(
        default=None, ge=0, description="Total file size if known"
    )


class DownloadProgressEvent(DownloadEvent):
    """Fired periodically when tracker records download progress."""

    event_type: str = Field(default="tracker.progress")
    bytes_downloaded: int = Field(
        default=0, ge=0, description="Bytes downloaded so far"
    )
    total_bytes: int | None = Field(
        default=None, ge=0, description="Total file size if known"
    )

    @computed_field  # type: ignore [prop-decorator]
    @property
    def progress_fraction(self) -> float:
        """Get progress as a fraction (0.0 to 1.0)."""
        if self.total_bytes is None or self.total_bytes == 0:
            return 0.0
        return min(self.bytes_downloaded / self.total_bytes, 1.0)

    @computed_field  # type: ignore [prop-decorator]
    @property
    def progress_percent(self) -> float:
        """Get progress as a percentage (0.0 to 100.0)."""
        return self.progress_fraction * 100.0


class DownloadCompletedEvent(DownloadEvent):
    """Fired when tracker records a download completed successfully."""

    event_type: str = Field(default="tracker.completed")
    destination_path: str = Field(default="", description="Path where file was saved")
    total_bytes: int = Field(default=0, ge=0, description="Total bytes downloaded")


class DownloadFailedEvent(DownloadEvent):
    """Fired when tracker records a download failed.

    TODO: Replace error_message/error_type with ErrorInfo model
    """

    event_type: str = Field(default="tracker.failed")
    error_message: str = Field(default="", description="Error message")
    error_type: str = Field(default="", description="Exception type name")


class DownloadValidationStartedEvent(DownloadEvent):
    """Fired when hash validation starts."""

    event_type: str = Field(default="tracker.validation_started")
    # TODO: Use HashAlgorithm enum from domain
    algorithm: str = Field(default="", description="Hash algorithm used")


class DownloadValidationCompletedEvent(DownloadEvent):
    """Fired when hash validation succeeds."""

    event_type: str = Field(default="tracker.validation_completed")
    # TODO: Use HashAlgorithm enum from domain
    algorithm: str = Field(default="", description="Hash algorithm used")
    calculated_hash: str = Field(default="", description="Computed hash value")


class DownloadValidationFailedEvent(DownloadEvent):
    """Fired when hash validation fails.

    TODO: Replace error_message with ErrorInfo model
    """

    event_type: str = Field(default="tracker.validation_failed")
    # TODO: Use HashAlgorithm enum from domain
    algorithm: str = Field(default="", description="Hash algorithm used")
    expected_hash: str = Field(default="", description="Expected hash value")
    actual_hash: str | None = Field(default=None, description="Actual computed hash")
    error_message: str = Field(default="", description="Error description")
