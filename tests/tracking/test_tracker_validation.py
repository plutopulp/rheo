"""Tests for DownloadTracker validation state tracking."""

import pytest

from rheo.domain.hash_validation import ValidationStatus
from rheo.tracking import DownloadTracker


@pytest.mark.asyncio
async def test_track_validation_started_updates_state(tracker: DownloadTracker) -> None:
    """track_validation_started sets validation status to IN_PROGRESS."""
    download_id = "test-id"
    url = "https://example.com/file.txt"

    await tracker.track_validation_started(download_id, url, algorithm="sha256")

    info = tracker.get_download_info(download_id)
    assert info is not None
    assert info.validation is not None
    assert info.validation.status == ValidationStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_track_validation_completed_updates_state(
    tracker: DownloadTracker,
) -> None:
    """track_validation_completed records hash and sets status to SUCCEEDED."""
    download_id = "test-id"
    url = "https://example.com/file.txt"
    await tracker.track_validation_started(download_id, url, algorithm="sha256")

    await tracker.track_validation_completed(
        download_id,
        url,
        algorithm="sha256",
        calculated_hash="abc123",
    )

    info = tracker.get_download_info(download_id)
    assert info is not None
    assert info.validation is not None
    assert info.validation.status == ValidationStatus.SUCCEEDED
    assert info.validation.calculated_hash == "abc123"
    assert info.validation.error is None


@pytest.mark.asyncio
async def test_track_validation_failed_updates_state(tracker: DownloadTracker) -> None:
    """track_validation_failed records error details and sets status to FAILED."""
    download_id = "test-id"
    url = "https://example.com/file.txt"
    await tracker.track_validation_started(download_id, url, algorithm="sha256")

    await tracker.track_validation_failed(
        download_id,
        url,
        algorithm="sha256",
        expected_hash="expected",
        actual_hash="actual",
        error_message="hash mismatch",
    )

    info = tracker.get_download_info(download_id)
    assert info is not None
    assert info.validation is not None
    assert info.validation.status == ValidationStatus.FAILED
    assert info.validation.calculated_hash == "actual"
    assert info.validation.error == "hash mismatch"
