"""Pytest configuration and fixtures for async-download-manager tests."""

import loguru
import pytest
import pytest_asyncio
from aiohttp import ClientSession

from async_download_manager.app import create_app
from async_download_manager.config.settings import Environment, Settings
from async_download_manager.downloads import DownloadManager
from async_download_manager.events import BaseEmitter
from async_download_manager.infrastructure.logging import reset_logging
from async_download_manager.tracking import DownloadTracker


@pytest.fixture
def test_settings():
    """Provide test-specific settings."""
    return Settings(
        environment=Environment.TESTING,
        log_level="CRITICAL",  # Minimal logging during tests
    )


@pytest.fixture
def test_app(test_settings):
    """Provide a test app with clean logging state."""
    # Reset logging before creating app to ensure clean state
    reset_logging()
    app = create_app(settings=test_settings)
    yield app
    # Clean up after test
    reset_logging()


@pytest.fixture
def mock_logger(mocker):
    """Provide a mock logger for testing that captures log calls."""
    logger = mocker.Mock(spec=loguru.logger)
    return logger


@pytest.fixture
def mock_emitter(mocker):
    """Provide a mock event emitter for testing event emission."""

    emitter = mocker.Mock(spec=BaseEmitter)
    emitter.emit = mocker.AsyncMock()
    return emitter


@pytest.fixture(autouse=True)
def clean_logging_state():
    """Automatically reset logging before each test for isolation."""
    reset_logging()
    yield
    # Cleanup after test (optional, but good practice)
    reset_logging()


@pytest_asyncio.fixture
async def aio_client():
    """Provide a real aiohttp ClientSession for integration testing."""
    session = ClientSession()
    yield session
    await session.close()


@pytest.fixture
def tracker(mock_logger):
    """Provide a DownloadTracker with mocked logger for testing."""
    return DownloadTracker(logger=mock_logger)


@pytest.fixture
def manager_with_tracker(aio_client, tracker, mock_logger):
    """Provide a DownloadManager with tracker wired for integration testing."""
    return DownloadManager(
        client=aio_client,
        tracker=tracker,
        logger=mock_logger,
    )
