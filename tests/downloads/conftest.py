"""Fixtures for download operation tests."""

import asyncio
import hashlib

import pytest
from aiohttp import ClientSession

from async_download_manager.domain.file_config import FileConfig
from async_download_manager.domain.hash_validation import HashAlgorithm
from async_download_manager.domain.retry import RetryConfig
from async_download_manager.downloads import (
    DownloadManager,
    DownloadWorker,
    ErrorCategoriser,
    PriorityDownloadQueue,
    RetryHandler,
)
from async_download_manager.events import EventEmitter


@pytest.fixture
def calculate_hash():
    """Factory fixture to calculate hash for test content.

    Common helper for hash validation tests to avoid duplication.
    Returns a function that calculates hashes.

    Usage:
        def test_something(calculate_hash):
            hash_value = calculate_hash(b"content", HashAlgorithm.SHA256)
    """

    def _calculate(content: bytes, algorithm: HashAlgorithm) -> str:
        hasher = hashlib.new(algorithm)
        hasher.update(content)
        return hasher.hexdigest()

    return _calculate


@pytest.fixture
def mock_aio_client(mocker):
    """Provide a mocked aiohttp ClientSession for unit tests."""
    mock_client = mocker.Mock(spec=ClientSession)
    mock_client.closed = False
    return mock_client


@pytest.fixture
def mock_worker(mocker):
    """Provide a mocked DownloadWorker for unit tests."""
    worker = mocker.Mock(spec=DownloadWorker)
    worker.download = mocker.AsyncMock()
    return worker


@pytest.fixture
def test_worker(aio_client, mock_logger):
    """Provide a real DownloadWorker with real client and mocked logger."""
    return DownloadWorker(aio_client, mock_logger)


@pytest.fixture
def fast_retry_config():
    """Provide a RetryConfig with fast retries for testing.

    Uses minimal delays and no jitter to speed up retry tests.
    """

    return RetryConfig(
        max_retries=2,
        base_delay=0.01,  # 10ms base delay
        max_delay=0.1,  # 100ms max delay
        jitter=False,  # Deterministic timing for tests
    )


@pytest.fixture
def test_worker_with_retry(aio_client, mock_logger, fast_retry_config):
    """Provide a DownloadWorker with retry handler for validation tests.

    Uses fast_retry_config for quick test execution.
    """
    emitter = EventEmitter(mock_logger)
    categoriser = ErrorCategoriser(fast_retry_config.policy)
    retry_handler = RetryHandler(
        config=fast_retry_config,
        logger=mock_logger,
        emitter=emitter,
        categoriser=categoriser,
    )

    return DownloadWorker(
        client=aio_client,
        logger=mock_logger,
        emitter=emitter,
        retry_handler=retry_handler,
    )


@pytest.fixture
def worker_with_real_events(aio_client, mock_logger, fast_retry_config):
    """Provide a DownloadWorker with retry handler and real EventEmitter.

    Uses fast_retry_config for quick test execution. Includes a real
    EventEmitter (not mocked) for testing actual event emission and handlers.

    Use this when you need to test event subscribers that react to events
    (e.g., speed tracking, retry event handlers).
    """

    emitter = EventEmitter(mock_logger)
    categoriser = ErrorCategoriser(fast_retry_config.policy)
    retry_handler = RetryHandler(
        config=fast_retry_config,
        logger=mock_logger,
        emitter=emitter,
        categoriser=categoriser,
    )

    return DownloadWorker(
        client=aio_client,
        logger=mock_logger,
        emitter=emitter,
        retry_handler=retry_handler,
    )


@pytest.fixture
def real_priority_queue(mock_logger):
    """Provide a real PriorityDownloadQueue with injected asyncio.PriorityQueue."""
    async_queue = asyncio.PriorityQueue()
    return PriorityDownloadQueue(queue=async_queue, logger=mock_logger)


@pytest.fixture
def mock_manager_dependencies(mock_aio_client, mock_worker, mock_queue):
    """Provide all mocked dependencies for DownloadManager tests."""
    return {
        "client": mock_aio_client,
        "worker": mock_worker,
        "queue": mock_queue,
    }


@pytest.fixture
def make_file_config():
    """Factory fixture to create FileConfig instances with sensible defaults."""

    def _make_file_config(
        url: str = "https://example.com/test.txt", priority: int = 1, **kwargs
    ) -> FileConfig:
        return FileConfig(url=url, priority=priority, **kwargs)

    return _make_file_config


@pytest.fixture
def make_file_configs(make_file_config):
    """Factory fixture to create lists of FileConfig instances."""

    def _make_file_configs(
        count: int = 1,
        url_template: str = "https://example.com/file{}.txt",
        priorities: list[int] | None = None,
        base_priority: int = 1,
    ) -> list[FileConfig]:
        configs = []
        for i in range(count):
            url = url_template.format(i)
            priority = priorities[i] if priorities else base_priority
            configs.append(make_file_config(url=url, priority=priority))
        return configs

    return _make_file_configs


@pytest.fixture
def make_shutdown_manager(
    mock_aio_client, mock_worker, real_priority_queue, mock_logger, tmp_path
):
    """Factory fixture to create DownloadManager for shutdown tests.

    Returns a factory function that creates managers with customizable max_workers.
    All managers share the same mocked dependencies from the test.
    """

    def _create_manager(max_workers: int = 1):
        return DownloadManager(
            client=mock_aio_client,
            worker=mock_worker,
            queue=real_priority_queue,
            max_workers=max_workers,
            download_dir=tmp_path,
            logger=mock_logger,
        )

    return _create_manager


@pytest.fixture
def slow_download_mock():
    """Factory to create mock download functions with timing control.

    Returns a factory that creates async mock functions with:
    - started: Event that sets when download begins
    - completed: Event that sets when download finishes
    - Configurable download_time duration
    """

    def _create_mock(download_time: float = 0.1):
        download_started = asyncio.Event()
        download_completed = asyncio.Event()

        async def mock_download(*args, **kwargs):
            download_started.set()
            await asyncio.sleep(download_time)
            download_completed.set()

        # Attach events for verification
        mock_download.started = download_started
        mock_download.completed = download_completed
        return mock_download

    return _create_mock


@pytest.fixture
def counting_download_mock():
    """Factory to create mock download functions that count invocations.

    Returns a factory that creates async mock functions with:
    - count: Dict with 'value' key tracking invocation count
    - Configurable download_time duration
    """

    def _create_mock(download_time: float = 0.05):
        count = {"value": 0}

        async def mock_download(*args, **kwargs):
            count["value"] += 1
            await asyncio.sleep(download_time)

        # Attach count for easy access
        mock_download.count = count
        return mock_download

    return _create_mock
