"""Tests for WorkerEvent classes."""

import pytest
from pydantic import ValidationError

from rheo.events import (
    WorkerCompletedEvent,
    WorkerProgressEvent,
    WorkerRetryEvent,
    WorkerSpeedUpdatedEvent,
    WorkerValidationCompletedEvent,
)


class TestWorkerEventConstraints:
    """Test field constraints on worker events."""

    def test_bytes_downloaded_rejects_negative(self) -> None:
        """bytes_downloaded must be >= 0."""
        with pytest.raises(ValidationError):
            WorkerProgressEvent(
                download_id="test",
                url="https://example.com",
                bytes_downloaded=-1,
            )

    def test_chunk_size_rejects_negative(self) -> None:
        """chunk_size must be >= 0."""
        with pytest.raises(ValidationError):
            WorkerProgressEvent(
                download_id="test",
                url="https://example.com",
                chunk_size=-1,
            )

    def test_total_bytes_rejects_negative(self) -> None:
        """total_bytes must be >= 0."""
        with pytest.raises(ValidationError):
            WorkerCompletedEvent(
                download_id="test",
                url="https://example.com",
                total_bytes=-1,
            )

    def test_attempt_rejects_zero(self) -> None:
        """attempt must be >= 1 (1-indexed)."""
        with pytest.raises(ValidationError):
            WorkerRetryEvent(
                download_id="test",
                url="https://example.com",
                attempt=0,
                max_retries=3,
            )

    def test_attempt_rejects_negative(self) -> None:
        """attempt must be >= 1."""
        with pytest.raises(ValidationError):
            WorkerRetryEvent(
                download_id="test",
                url="https://example.com",
                attempt=-1,
                max_retries=3,
            )

    def test_duration_ms_rejects_negative(self) -> None:
        """duration_ms must be >= 0."""
        with pytest.raises(ValidationError):
            WorkerValidationCompletedEvent(
                download_id="test",
                url="https://example.com",
                duration_ms=-1.0,
            )

    def test_elapsed_seconds_rejects_negative(self) -> None:
        """elapsed_seconds must be >= 0."""
        with pytest.raises(ValidationError):
            WorkerSpeedUpdatedEvent(
                download_id="test",
                url="https://example.com",
                elapsed_seconds=-1.0,
            )
