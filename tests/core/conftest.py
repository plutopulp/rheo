import asyncio

import pytest
import pytest_asyncio
from aiohttp import ClientSession

from async_download_manager.core.models import FileConfig
from async_download_manager.core.queue import PriorityDownloadQueue
from async_download_manager.core.worker import DownloadWorker


@pytest.fixture
def test_logger(mocker):
    """Provide a mock logger for testing that captures log calls."""
    logger = mocker.Mock()
    # Configure mock methods to avoid AttributeErrors
    logger.debug = mocker.Mock()
    logger.info = mocker.Mock()
    logger.warning = mocker.Mock()
    logger.error = mocker.Mock()
    logger.critical = mocker.Mock()
    return logger


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
def real_priority_queue(test_logger):
    """Provide a real PriorityDownloadQueue with injected asyncio.PriorityQueue.

    Useful for integration tests that need a functioning queue but want to
    control the underlying asyncio.PriorityQueue for testing concurrency.
    """
    async_queue = asyncio.PriorityQueue()
    return PriorityDownloadQueue(queue=async_queue, logger=test_logger)


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
