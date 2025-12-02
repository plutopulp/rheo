"""Tests for DownloadEvent classes."""

import pytest
from pydantic import ValidationError

from rheo.events import (
    DownloadCompletedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
)


class TestTrackerEventConstraints:
    """Test field constraints on tracker events."""

    def test_priority_rejects_zero(self) -> None:
        """priority must be >= 1."""
        with pytest.raises(ValidationError):
            DownloadQueuedEvent(
                download_id="test",
                url="https://example.com",
                priority=0,
            )

    def test_bytes_downloaded_rejects_negative(self) -> None:
        """bytes_downloaded must be >= 0."""
        with pytest.raises(ValidationError):
            DownloadProgressEvent(
                download_id="test",
                url="https://example.com",
                bytes_downloaded=-1,
            )

    def test_total_bytes_rejects_negative(self) -> None:
        """total_bytes must be >= 0."""
        with pytest.raises(ValidationError):
            DownloadCompletedEvent(
                download_id="test",
                url="https://example.com",
                total_bytes=-1,
            )
