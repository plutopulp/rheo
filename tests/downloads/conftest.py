"""Fixtures for download operation tests."""

import asyncio

import pytest
import pytest_asyncio
from aiohttp import ClientSession

from async_download_manager.domain.downloads import FileConfig
from async_download_manager.downloads import (
    DownloadManager,
    DownloadWorker,
    PriorityDownloadQueue,
)


@pytest_asyncio.fixture
async def aio_client():
    """Provide a real aiohttp ClientSession for integration testing."""
    session = ClientSession()
    yield session
    await session.close()


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
def mock_queue(mocker):
    """Provide a mocked PriorityDownloadQueue for unit tests."""
    queue = mocker.Mock(spec=PriorityDownloadQueue)
    queue.add = mocker.AsyncMock()
    queue.get_next = mocker.AsyncMock()
    queue.task_done = mocker.Mock()
    queue.is_empty = mocker.Mock(return_value=False)
    queue.size = mocker.Mock(return_value=0)
    queue.join = mocker.AsyncMock()
    return queue


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
def manager_with_tracker(aio_client, tracker, mock_logger):
    """Provide a DownloadManager with tracker wired for integration testing."""
    return DownloadManager(
        client=aio_client,
        tracker=tracker,
        logger=mock_logger,
    )


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
