"""Tests for DownloadTracker validation tracking."""

import pytest

from rheo.domain.hash_validation import ValidationStatus
from rheo.events import (
    DownloadValidationCompletedEvent,
    DownloadValidationFailedEvent,
    DownloadValidationStartedEvent,
)
from rheo.tracking import DownloadTracker


@pytest.mark.asyncio
async def test_track_validation_started_updates_state(tracker: DownloadTracker) -> None:
    """track_validation_started updates state and emits event."""
    url = "https://example.com/file.txt"
    events: list[DownloadValidationStartedEvent] = []
    tracker.on("tracker.validation_started", lambda event: events.append(event))

    await tracker.track_validation_started(url, algorithm="sha256")

    info = tracker.get_download_info(url)
    assert info is not None
    assert info.validation is not None
    assert info.validation.status == ValidationStatus.IN_PROGRESS
    assert isinstance(events[0], DownloadValidationStartedEvent)
    assert events[0].algorithm == "sha256"


@pytest.mark.asyncio
async def test_track_validation_completed_updates_state(
    tracker: DownloadTracker,
) -> None:
    """track_validation_completed records hash and emits event."""
    url = "https://example.com/file.txt"
    await tracker.track_validation_started(url, algorithm="sha256")

    events: list[DownloadValidationCompletedEvent] = []
    tracker.on("tracker.validation_completed", lambda event: events.append(event))

    await tracker.track_validation_completed(
        url,
        algorithm="sha256",
        calculated_hash="abc123",
    )

    info = tracker.get_download_info(url)
    assert info is not None
    assert info.validation is not None
    assert info.validation.status == ValidationStatus.SUCCEEDED
    assert info.validation.validated_hash == "abc123"
    assert info.validation.error is None
    assert isinstance(events[0], DownloadValidationCompletedEvent)
    assert events[0].calculated_hash == "abc123"


@pytest.mark.asyncio
async def test_track_validation_failed_updates_state(tracker: DownloadTracker) -> None:
    """track_validation_failed records error details."""
    url = "https://example.com/file.txt"
    await tracker.track_validation_started(url, algorithm="sha256")

    events: list[DownloadValidationFailedEvent] = []
    tracker.on("tracker.validation_failed", lambda event: events.append(event))

    await tracker.track_validation_failed(
        url=url,
        algorithm="sha256",
        expected_hash="expected",
        actual_hash="actual",
        error_message="hash mismatch",
    )

    info = tracker.get_download_info(url)
    assert info is not None
    assert info.validation is not None
    assert info.validation.status == ValidationStatus.FAILED
    assert info.validation.validated_hash == "actual"
    assert info.validation.error == "hash mismatch"
    assert isinstance(events[0], DownloadValidationFailedEvent)
    assert events[0].expected_hash == "expected"
