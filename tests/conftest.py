"""Pytest configuration and fixtures for rheo tests."""

import typing as t

import loguru
import pytest
import pytest_asyncio
from aiohttp import ClientSession
from blockbuster import BlockBuster, blockbuster_ctx
from typer.testing import CliRunner

from rheo.app import create_app
from rheo.cli.app import create_cli_app
from rheo.config.settings import Environment, LogLevel, Settings
from rheo.downloads import DownloadManager, PriorityDownloadQueue
from rheo.events import BaseEmitter, EventEmitter
from rheo.infrastructure.logging import reset_logging
from rheo.tracking import DownloadTracker


@pytest.fixture(autouse=True)
def blockbuster() -> t.Iterator[BlockBuster]:
    """Detect blocking calls in async event loop during tests.

    This fixture automatically activates Blockbuster for all tests,
    which will raise a BlockingError if any blocking I/O operations
    (like synchronous file.write()) are called within an async context.
    """
    with blockbuster_ctx(
        scanned_modules=["rheo"],
    ) as bb:
        # Third party modules use these functions, so we deactivate them
        # for now
        bb.functions["os.path.abspath"].deactivate()

        yield bb


@pytest.fixture
def test_settings():
    """Provide test-specific settings."""
    return Settings(
        environment=Environment.TESTING,
        log_level=LogLevel.CRITICAL,  # Minimal logging during tests
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
    return emitter


@pytest.fixture
def mock_queue(mocker):
    """Provide a mocked PriorityDownloadQueue for unit tests."""
    queue = mocker.Mock(spec=PriorityDownloadQueue)
    return queue


@pytest.fixture
def real_emitter(mock_logger):
    """Provide a real EventEmitter for testing actual event emission.

    Use this when you need to test event handlers or subscribers that
    actually receive and process events (e.g., speed tracking, retry events).

    For simple tests that only verify emit() was called, use mock_emitter instead.
    """

    return EventEmitter(mock_logger)


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
def manager_with_tracker(aio_client, tracker, mock_logger, tmp_path):
    """Provide a DownloadManager with tracker wired for integration testing."""
    return DownloadManager(
        client=aio_client,
        tracker=tracker,
        logger=mock_logger,
        download_dir=tmp_path,
    )


# CLI-specific fixtures (shared across all tests)


@pytest.fixture
def cli_runner():
    """Provide Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def default_app():
    """Provide CLI app with default settings."""
    return create_cli_app()
