"""Tests for DownloadWorker hash validation integration."""

import typing as t
from dataclasses import dataclass
from pathlib import Path

import pytest
from aioresponses import aioresponses

from rheo.domain.exceptions import HashMismatchError
from rheo.domain.hash_validation import HashAlgorithm, HashConfig
from rheo.downloads.worker.base import BaseWorker
from rheo.events import (
    DownloadCompletedEvent,
    DownloadFailedEvent,
    DownloadValidatingEvent,
)


@dataclass
class ValidationTestData:
    """Test data container for validation tests."""

    url: str
    content: bytes
    path: Path


@pytest.fixture
def validation_test_data(tmp_path: Path) -> ValidationTestData:
    """Provide test data for hash validation tests.

    Returns a simple dataclass-like object with url, content, and path.
    Content is generic enough for most validation scenarios.
    """
    return ValidationTestData(
        url="https://example.com/file.txt",
        content=b"test content for validation",
        path=tmp_path / "file.txt",
    )


class TestWorkerValidationSuccess:
    """Test successful validation scenarios."""

    @pytest.mark.asyncio
    async def test_download_with_valid_hash_succeeds(
        self,
        test_worker: BaseWorker,
        calculate_hash: t.Callable[[bytes, str], str],
        validation_test_data: ValidationTestData,
    ) -> None:
        """Download with matching hash completes successfully."""
        hash_config = HashConfig(
            algorithm=HashAlgorithm.SHA256,
            expected_hash=calculate_hash(
                validation_test_data.content, HashAlgorithm.SHA256
            ),
        )

        with aioresponses() as mock:
            mock.get(
                validation_test_data.url, status=200, body=validation_test_data.content
            )
            await test_worker.download(
                validation_test_data.url,
                validation_test_data.path,
                download_id="test-id",
                hash_config=hash_config,
            )

        assert validation_test_data.path.exists()
        assert validation_test_data.path.read_bytes() == validation_test_data.content

    @pytest.mark.asyncio
    async def test_download_without_hash_config_skips_validation(
        self, test_worker: BaseWorker, validation_test_data: ValidationTestData
    ) -> None:
        """Download without hash_config skips validation entirely."""
        validating_events: list[DownloadValidatingEvent] = []
        test_worker.emitter.on("download.validating", validating_events.append)

        with aioresponses() as mock:
            mock.get(
                validation_test_data.url, status=200, body=validation_test_data.content
            )
            await test_worker.download(
                validation_test_data.url,
                validation_test_data.path,
                download_id="test-id",
            )

        assert validation_test_data.path.exists()
        assert len(validating_events) == 0


class TestWorkerValidationEvents:
    """Test validation event emission."""

    @pytest.mark.asyncio
    async def test_emits_validating_event(
        self,
        test_worker: BaseWorker,
        calculate_hash: t.Callable[[bytes, str], str],
        validation_test_data: ValidationTestData,
    ) -> None:
        """Worker emits download.validating event when validation starts."""
        hash_config = HashConfig(
            algorithm=HashAlgorithm.MD5,
            expected_hash=calculate_hash(
                validation_test_data.content, HashAlgorithm.MD5
            ),
        )

        events: list[DownloadValidatingEvent] = []
        test_worker.emitter.on("download.validating", events.append)

        with aioresponses() as mock:
            mock.get(
                validation_test_data.url, status=200, body=validation_test_data.content
            )
            await test_worker.download(
                validation_test_data.url,
                validation_test_data.path,
                download_id="test-id",
                hash_config=hash_config,
            )

        assert len(events) == 1
        assert isinstance(events[0], DownloadValidatingEvent)
        assert events[0].url == validation_test_data.url
        assert events[0].algorithm == HashAlgorithm.MD5

    @pytest.mark.asyncio
    async def test_completed_event_includes_validation_result(
        self,
        test_worker: BaseWorker,
        calculate_hash: t.Callable[[bytes, str], str],
        validation_test_data: ValidationTestData,
    ) -> None:
        """On success, download.completed includes validation result."""
        expected_hash = calculate_hash(
            validation_test_data.content, HashAlgorithm.SHA256
        )
        hash_config = HashConfig(
            algorithm=HashAlgorithm.SHA256,
            expected_hash=expected_hash,
        )

        events: list[DownloadCompletedEvent] = []
        test_worker.emitter.on("download.completed", events.append)

        with aioresponses() as mock:
            mock.get(
                validation_test_data.url, status=200, body=validation_test_data.content
            )
            await test_worker.download(
                validation_test_data.url,
                validation_test_data.path,
                download_id="test-id",
                hash_config=hash_config,
            )

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, DownloadCompletedEvent)
        assert event.validation is not None
        assert event.validation.algorithm == HashAlgorithm.SHA256
        assert event.validation.expected_hash == expected_hash
        assert event.validation.calculated_hash == expected_hash
        assert event.validation.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_validation_result_has_actual_calculated_hash(
        self,
        test_worker: BaseWorker,
        calculate_hash: t.Callable[[bytes, str], str],
        validation_test_data: ValidationTestData,
    ) -> None:
        """ValidationResult.calculated_hash is derived from file content.

        This test verifies that calculated_hash in the event is derived from
        the file content, not just echoed from hash_config.expected_hash.
        The validator should return what it actually computed.
        """
        expected_hash = calculate_hash(
            validation_test_data.content, HashAlgorithm.SHA256
        )
        hash_config = HashConfig(
            algorithm=HashAlgorithm.SHA256,
            expected_hash=expected_hash,
        )

        events: list[DownloadCompletedEvent] = []
        test_worker.emitter.on("download.completed", events.append)

        with aioresponses() as mock:
            mock.get(
                validation_test_data.url, status=200, body=validation_test_data.content
            )
            await test_worker.download(
                validation_test_data.url,
                validation_test_data.path,
                download_id="test-id",
                hash_config=hash_config,
            )

        # Verify file was written
        assert validation_test_data.path.exists()

        # Calculate hash directly from the downloaded file
        actual_file_content = validation_test_data.path.read_bytes()
        actual_file_hash = calculate_hash(actual_file_content, HashAlgorithm.SHA256)

        # The event's calculated_hash should match what we compute from the file
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, DownloadCompletedEvent)
        assert event.validation is not None
        assert event.validation.calculated_hash == actual_file_hash
        assert event.validation.calculated_hash == expected_hash

    @pytest.mark.asyncio
    async def test_failed_event_includes_validation_on_mismatch(
        self, test_worker: BaseWorker, validation_test_data: ValidationTestData
    ) -> None:
        """On hash mismatch, download.failed includes validation result."""
        hash_config = HashConfig(
            algorithm=HashAlgorithm.SHA512,
            expected_hash="a" * HashAlgorithm.SHA512.hex_length,
        )

        events: list[DownloadFailedEvent] = []
        test_worker.emitter.on("download.failed", events.append)

        with aioresponses() as mock:
            mock.get(
                validation_test_data.url, status=200, body=validation_test_data.content
            )
            with pytest.raises(HashMismatchError):
                await test_worker.download(
                    validation_test_data.url,
                    validation_test_data.path,
                    download_id="test-id",
                    hash_config=hash_config,
                )

        assert len(events) == 1
        assert isinstance(events[0], DownloadFailedEvent)
        assert events[0].validation is not None
        assert events[0].validation.algorithm == HashAlgorithm.SHA512
        assert events[0].validation.expected_hash == hash_config.expected_hash
        assert events[0].validation.calculated_hash is not None
        # Verify error info indicates hash mismatch
        assert "HashMismatchError" in events[0].error.exc_type


class TestWorkerValidationFailures:
    """Test validation failure scenarios."""

    @pytest.mark.asyncio
    async def test_hash_mismatch_raises_and_cleans_up(
        self, test_worker: BaseWorker, validation_test_data: ValidationTestData
    ) -> None:
        """Hash mismatch raises error and removes file."""
        hash_config = HashConfig(
            algorithm=HashAlgorithm.MD5,
            expected_hash="f" * HashAlgorithm.MD5.hex_length,
        )

        with aioresponses() as mock:
            mock.get(
                validation_test_data.url, status=200, body=validation_test_data.content
            )
            with pytest.raises(HashMismatchError) as exc_info:
                await test_worker.download(
                    validation_test_data.url,
                    validation_test_data.path,
                    download_id="test-id",
                    hash_config=hash_config,
                )

        assert exc_info.value.expected_hash == hash_config.expected_hash
        assert exc_info.value.calculated_hash is not None
        assert not validation_test_data.path.exists()  # File should be cleaned up

    @pytest.mark.asyncio
    async def test_download_completes_event_not_emitted_on_validation_failure(
        self, test_worker: BaseWorker, validation_test_data: ValidationTestData
    ) -> None:
        """download.completed event not emitted when validation fails."""
        hash_config = HashConfig(
            algorithm=HashAlgorithm.SHA256,
            expected_hash="0" * HashAlgorithm.SHA256.hex_length,
        )

        completed_events = []
        test_worker.emitter.on("download.completed", completed_events.append)

        with aioresponses() as mock:
            mock.get(
                validation_test_data.url, status=200, body=validation_test_data.content
            )
            with pytest.raises(HashMismatchError):
                await test_worker.download(
                    validation_test_data.url,
                    validation_test_data.path,
                    download_id="test-id",
                    hash_config=hash_config,
                )

        assert len(completed_events) == 0


class TestWorkerValidationWithRetry:
    """Test validation interaction with retry handler."""

    @pytest.mark.asyncio
    async def test_validation_failure_not_retried_by_default(
        self,
        test_worker_with_retry: BaseWorker,
        validation_test_data: ValidationTestData,
    ) -> None:
        """Hash mismatch is not retried (permanent error).

        TODO: Future enhancement - add retry_on_mismatch configuration to
        HashConfig to allow retrying validation failures in case of network
        corruption during transfer.
        """
        hash_config = HashConfig(
            algorithm=HashAlgorithm.SHA256,
            expected_hash="1" * HashAlgorithm.SHA256.hex_length,
        )

        validation_attempts: list[DownloadValidatingEvent] = []
        test_worker_with_retry.emitter.on(
            "download.validating", validation_attempts.append
        )

        with aioresponses() as mock:
            # Mock multiple responses in case retry happens
            mock.get(
                validation_test_data.url, status=200, body=validation_test_data.content
            )
            mock.get(
                validation_test_data.url, status=200, body=validation_test_data.content
            )

            with pytest.raises(HashMismatchError):
                await test_worker_with_retry.download(
                    validation_test_data.url,
                    validation_test_data.path,
                    download_id="test-id",
                    hash_config=hash_config,
                )

        # Should only attempt validation once (not retried)
        assert len(validation_attempts) == 1
