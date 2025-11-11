import asyncio

import loguru
import pytest
import pytest_asyncio
from aiohttp import ClientSession

from async_download_manager.core.manager import DownloadManager
from async_download_manager.core.models import FileConfig
from async_download_manager.core.null_emitter import NullEmitter
from async_download_manager.core.null_tracker import NullTracker
from async_download_manager.core.queue import PriorityDownloadQueue
from async_download_manager.core.tracker import DownloadTracker
from async_download_manager.core.worker import DownloadWorker


@pytest.fixture
def mock_logger(mocker):
    """Provide a mock logger for testing that captures log calls."""
    logger = mocker.Mock(spec=loguru.logger)
    return logger


@pytest.fixture
def tracker(mock_logger):
    """Provide a DownloadTracker with mocked logger for testing.

    This fixture creates a DownloadTracker with the mock_logger injected,
    allowing tests to verify logging behavior while testing tracker functionality.

    Tests can override specific attributes as needed:
        def test_something(mock_tracker):
            # Use tracker with mocked logger
            await mock_tracker.track_queued("https://example.com")

            # Verify logger was called
            mock_tracker._logger.debug.assert_called()
    """
    return DownloadTracker(logger=mock_logger)


@pytest_asyncio.fixture
async def aio_client():
    """Provide a real aiohttp ClientSession for integration testing."""
    session = ClientSession()
    yield session
    await session.close()


@pytest.fixture
def mock_aio_client(mocker):
    """Provide a mocked aiohttp ClientSession for unit tests.

    This fixture should be used for unit tests that don't need real HTTP functionality.
    For integration tests that need actual HTTP behavior (with aioresponses),
    use aio_client.
    """
    mock_client = mocker.Mock(spec=ClientSession)
    mock_client.closed = False
    return mock_client


@pytest.fixture
def mock_worker(mocker):
    """Provide a mocked DownloadWorker for unit tests.

    The worker's download method is configured as an AsyncMock by default.
    Tests can override the behavior by setting side_effect or return_value.

    Example:
        def test_something(mock_worker):
            mock_worker.download.side_effect = some_exception
    """
    worker = mocker.Mock(spec=DownloadWorker)
    worker.download = mocker.AsyncMock()
    return worker


@pytest.fixture
def test_worker(aio_client, mock_logger):
    """Provide a real DownloadWorker with real client and mocked logger.

    Useful for integration tests using aioresponses.
    """
    return DownloadWorker(aio_client, mock_logger)


@pytest.fixture
def mock_queue(mocker):
    """Provide a mocked PriorityDownloadQueue for unit tests.

    Common methods are pre-configured as AsyncMock/Mock.
    Tests can customize behavior as needed.

    Example:
        def test_something(mock_queue):
            mock_queue.get_next.side_effect = [file_config, asyncio.CancelledError()]
    """
    queue = mocker.Mock(spec=PriorityDownloadQueue)
    queue.add = mocker.AsyncMock()
    queue.get_next = mocker.AsyncMock()
    queue.task_done = mocker.Mock()
    queue.is_empty = mocker.Mock(return_value=False)
    queue.size = mocker.Mock(return_value=0)
    queue.join = mocker.AsyncMock()
    return queue


@pytest.fixture
def mock_manager_dependencies(mock_aio_client, mock_worker, mock_queue):
    """Provide all mocked dependencies for DownloadManager tests.

    Returns a dict with 'client', 'worker', and 'queue' keys.
    Useful for tests that need all three mocked dependencies.

    Example:
        def test_manager(mock_manager_dependencies):
            manager = DownloadManager(**mock_manager_dependencies)
    """
    return {
        "client": mock_aio_client,
        "worker": mock_worker,
        "queue": mock_queue,
    }


# ============================================================================
# Real Objects with DI
# ============================================================================


@pytest.fixture
def real_priority_queue(mock_logger):
    """Provide a real PriorityDownloadQueue with injected asyncio.PriorityQueue.

    Useful for integration tests that need a functioning queue but want to
    control the underlying asyncio.PriorityQueue for testing concurrency.
    """
    async_queue = asyncio.PriorityQueue()
    return PriorityDownloadQueue(queue=async_queue, logger=mock_logger)


@pytest.fixture
def null_tracker():
    """Provide a NullTracker instance for testing."""
    return NullTracker()


@pytest.fixture
def null_emitter():
    """Provide a NullEmitter instance for testing."""
    return NullEmitter()


@pytest.fixture
def manager_with_tracker(aio_client, tracker, mock_logger):
    """Provide a DownloadManager with tracker wired for integration testing.

    The manager is NOT entered as a context manager - tests should do that
    to control the lifecycle.
    """
    return DownloadManager(
        client=aio_client,
        tracker=tracker,
        logger=mock_logger,
    )


# ============================================================================
# Test Data Factories
# ============================================================================


@pytest.fixture
def make_file_config():
    """Factory fixture to create FileConfig instances with sensible defaults.

    Returns a callable that creates FileConfig objects.

    Examples:
        def test_something(make_file_config):
            config = make_file_config()  # Default URL and priority
            config = make_file_config(url="https://custom.com/file.txt")
            config = make_file_config(priority=5)
    """

    def _make_file_config(
        url: str = "https://example.com/test.txt", priority: int = 1, **kwargs
    ) -> FileConfig:
        return FileConfig(url=url, priority=priority, **kwargs)

    return _make_file_config


@pytest.fixture
def make_file_configs(make_file_config):
    """Factory fixture to create lists of FileConfig instances.

    Useful for tests that need multiple FileConfigs with varying priorities.

    Examples:
        def test_something(make_file_configs):
            # Create 5 configs with default settings
            configs = make_file_configs(count=5)

            # Create configs with specific URLs
            configs = make_file_configs(
                count=3,
                url_template="https://example.com/file{}.txt"
            )

            # Create configs with varying priorities
            configs = make_file_configs(count=3, priorities=[5, 3, 1])
    """

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
