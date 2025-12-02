"""Tests for WorkerValidationEvent classes."""

import pytest
from pydantic import ValidationError

from rheo.events import (
    WorkerValidationCompletedEvent,
    WorkerValidationStartedEvent,
)


class TestWorkerValidationEventConstraints:
    """Test field constraints on worker validation events."""

    def test_duration_ms_rejects_negative(self) -> None:
        """duration_ms must be >= 0."""
        with pytest.raises(ValidationError):
            WorkerValidationCompletedEvent(
                download_id="test",
                url="https://example.com",
                duration_ms=-1.0,
            )

    def test_file_size_bytes_rejects_negative(self) -> None:
        """file_size_bytes must be >= 0."""
        with pytest.raises(ValidationError):
            WorkerValidationStartedEvent(
                download_id="test",
                url="https://example.com",
                file_size_bytes=-1,
            )
