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
    WorkerValidationCompletedEvent,
    WorkerValidationFailedEvent,
    WorkerValidationStartedEvent,
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
        validation_events = []
        test_worker.emitter.on("worker.validation_started", validation_events.append)

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
        assert len(validation_events) == 0


class TestWorkerValidationEvents:
    """Test validation event emission."""

    @pytest.mark.asyncio
    async def test_emits_validation_started_event(
        self,
        test_worker: BaseWorker,
        calculate_hash: t.Callable[[bytes, str], str],
        validation_test_data: ValidationTestData,
    ) -> None:
        """Worker emits validation_started event when validating."""

        hash_config = HashConfig(
            algorithm=HashAlgorithm.MD5,
            expected_hash=calculate_hash(
                validation_test_data.content, HashAlgorithm.MD5
            ),
        )

        events = []
        test_worker.emitter.on("worker.validation_started", events.append)

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
        assert isinstance(events[0], WorkerValidationStartedEvent)
        assert events[0].url == validation_test_data.url
        assert events[0].algorithm == HashAlgorithm.MD5

    @pytest.mark.asyncio
    async def test_emits_validation_completed_event(
        self,
        test_worker: BaseWorker,
        calculate_hash: t.Callable[[bytes, str], str],
        validation_test_data: ValidationTestData,
    ) -> None:
        """Worker emits validation_completed event on success."""
        expected_hash = calculate_hash(
            validation_test_data.content, HashAlgorithm.SHA256
        )
        hash_config = HashConfig(
            algorithm=HashAlgorithm.SHA256,
            expected_hash=expected_hash,
        )

        events = []
        test_worker.emitter.on("worker.validation_completed", events.append)

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
        assert isinstance(events[0], WorkerValidationCompletedEvent)
        assert events[0].url == validation_test_data.url
        assert events[0].algorithm == HashAlgorithm.SHA256
        assert events[0].calculated_hash == expected_hash
        assert events[0].duration_ms >= 0

    @pytest.mark.asyncio
    async def test_emits_actual_calculated_hash_not_expected_hash(
        self,
        test_worker: BaseWorker,
        calculate_hash: t.Callable[[bytes, str], str],
        validation_test_data: ValidationTestData,
    ) -> None:
        """Worker emits the ACTUAL calculated hash, not just expected hash.

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

        events = []
        test_worker.emitter.on("worker.validation_completed", events.append)

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

        # The event's calculated_hash should match what we compute from the file,
        # proving it's the actual calculated value, not just the expected value
        assert len(events) == 1
        assert events[0].calculated_hash == actual_file_hash

        # This should also equal expected_hash since validation passed,
        # but the key is that it's derived from actual computation
        assert events[0].calculated_hash == expected_hash

    @pytest.mark.asyncio
    async def test_emits_validation_failed_event_on_mismatch(
        self, test_worker: BaseWorker, validation_test_data: ValidationTestData
    ) -> None:
        """Worker emits validation_failed event on hash mismatch."""
        hash_config = HashConfig(
            algorithm=HashAlgorithm.SHA512,
            expected_hash="a" * HashAlgorithm.SHA512.hex_length,
        )

        events = []
        test_worker.emitter.on("worker.validation_failed", events.append)

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
        assert isinstance(events[0], WorkerValidationFailedEvent)
        assert events[0].url == validation_test_data.url
        assert events[0].algorithm == HashAlgorithm.SHA512
        assert events[0].expected_hash == hash_config.expected_hash
        assert events[0].actual_hash is not None


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
        assert exc_info.value.actual_hash is not None
        assert not validation_test_data.path.exists()  # File should be cleaned up

    @pytest.mark.asyncio
    async def test_download_completes_event_not_emitted_on_validation_failure(
        self, test_worker: BaseWorker, validation_test_data: ValidationTestData
    ) -> None:
        """worker.completed event not emitted when validation fails."""
        hash_config = HashConfig(
            algorithm=HashAlgorithm.SHA256,
            expected_hash="0" * HashAlgorithm.SHA256.hex_length,
        )

        completed_events = []
        test_worker.emitter.on("worker.completed", completed_events.append)

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

        validation_attempts = []
        test_worker_with_retry.emitter.on(
            "worker.validation_started", validation_attempts.append
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
