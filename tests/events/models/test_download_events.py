"""Tests for download event classes."""

import pytest
from pydantic import ValidationError

from rheo.domain.speed import SpeedMetrics
from rheo.events.models import (
    DownloadCompletedEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadRetryingEvent,
    ErrorInfo,
)


class TestDownloadProgressEvent:
    """Test DownloadProgressEvent."""

    def test_progress_percent_calculated(self) -> None:
        """progress_percent should be computed from bytes/total."""
        event = DownloadProgressEvent(
            download_id="test", url="http://x", bytes_downloaded=50, total_bytes=100
        )
        assert event.progress_percent == 50.0

    def test_progress_percent_none_when_total_unknown(self) -> None:
        """progress_percent should be None if total_bytes is None."""
        event = DownloadProgressEvent(
            download_id="test", url="http://x", bytes_downloaded=50
        )
        assert event.progress_percent is None

    def test_progress_percent_none_when_total_zero(self) -> None:
        """progress_percent should be None if total_bytes is 0."""
        event = DownloadProgressEvent(
            download_id="test", url="http://x", bytes_downloaded=50, total_bytes=0
        )
        assert event.progress_percent is None

    def test_bytes_downloaded_rejects_negative(self) -> None:
        """bytes_downloaded must be >= 0."""
        with pytest.raises(ValidationError):
            DownloadProgressEvent(
                download_id="test", url="http://x", bytes_downloaded=-1
            )

    def test_speed_defaults_to_none(self) -> None:
        """speed should default to None (speed tracking disabled)."""
        event = DownloadProgressEvent(download_id="test", url="http://x")
        assert event.speed is None

    def test_speed_accepts_speed_metrics(self) -> None:
        """speed should accept SpeedMetrics model.

        SpeedMetrics constraints are tested in tests/domain/test_speed.py.
        """
        metrics = SpeedMetrics(
            current_speed_bps=1000.0,
            average_speed_bps=900.0,
            eta_seconds=10.0,
            elapsed_seconds=5.0,
        )
        event = DownloadProgressEvent(download_id="test", url="http://x", speed=metrics)
        assert event.speed is not None
        assert event.speed.current_speed_bps == 1000.0
        assert event.speed.average_speed_bps == 900.0


class TestDownloadCompletedEvent:
    """Test DownloadCompletedEvent."""

    def test_total_bytes_rejects_negative(self) -> None:
        """total_bytes must be >= 0."""
        with pytest.raises(ValidationError):
            DownloadCompletedEvent(download_id="test", url="http://x", total_bytes=-1)

    def test_elapsed_seconds_rejects_negative(self) -> None:
        """elapsed_seconds must be >= 0."""
        with pytest.raises(ValidationError):
            DownloadCompletedEvent(
                download_id="test", url="http://x", elapsed_seconds=-1.0
            )

    def test_average_speed_rejects_negative(self) -> None:
        """average_speed_bps must be >= 0."""
        with pytest.raises(ValidationError):
            DownloadCompletedEvent(
                download_id="test", url="http://x", average_speed_bps=-1.0
            )


class TestDownloadFailedEvent:
    """Test DownloadFailedEvent."""

    def test_requires_error_info(self) -> None:
        """error field should be required."""
        with pytest.raises(ValidationError):
            DownloadFailedEvent(download_id="test", url="http://x")

    def test_accepts_error_info(self) -> None:
        """Should accept ErrorInfo model."""
        error = ErrorInfo(exc_type="ValueError", message="test")
        event = DownloadFailedEvent(download_id="test", url="http://x", error=error)
        assert event.error.exc_type == "ValueError"


class TestDownloadRetryingEvent:
    """Test DownloadRetryingEvent."""

    def test_retry_must_be_positive(self) -> None:
        """retry must be >= 1."""
        error = ErrorInfo(exc_type="ValueError", message="test")
        with pytest.raises(ValidationError):
            DownloadRetryingEvent(
                download_id="test",
                url="http://x",
                retry=0,
                max_retries=2,
                error=error,
            )

    def test_max_retries_must_be_positive(self) -> None:
        """max_retries must be >= 1."""
        error = ErrorInfo(exc_type="ValueError", message="test")
        with pytest.raises(ValidationError):
            DownloadRetryingEvent(
                download_id="test",
                url="http://x",
                retry=1,
                max_retries=0,
                error=error,
            )

    def test_requires_error_info(self) -> None:
        """error field should be required."""
        with pytest.raises(ValidationError):
            DownloadRetryingEvent(
                download_id="test", url="http://x", retry=1, max_retries=2
            )


class TestDownloadQueuedEvent:
    """Test DownloadQueuedEvent."""

    def test_priority_must_be_positive(self) -> None:
        """priority must be >= 1."""
        with pytest.raises(ValidationError):
            DownloadQueuedEvent(download_id="test", url="http://x", priority=0)

    def test_accepts_valid_priority(self) -> None:
        """Should accept priority >= 1."""
        event = DownloadQueuedEvent(download_id="test", url="http://x", priority=5)
        assert event.priority == 5

    def test_event_type_is_download_queued(self) -> None:
        """event_type should be download.queued."""
        event = DownloadQueuedEvent(download_id="test", url="http://x", priority=1)
        assert event.event_type == "download.queued"
