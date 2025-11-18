"""Shared fixtures for CLI tests."""

import pytest
from typer.testing import CliRunner

from async_download_manager.cli.app import create_cli_app
from async_download_manager.cli.state import CLIState
from async_download_manager.config.settings import LogLevel, Settings
from async_download_manager.downloads import DownloadManager
from async_download_manager.tracking import DownloadTracker


@pytest.fixture
def cli_runner():
    """Provide Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def test_settings():
    """Provide test Settings with known values."""
    return Settings(
        max_workers=5,
        log_level=LogLevel.DEBUG,
        chunk_size=16384,
        timeout=600.0,
    )


@pytest.fixture
def test_app(test_settings):
    """Provide CLI app with test settings injected."""
    return create_cli_app(settings=test_settings)


@pytest.fixture
def default_app():
    """Provide CLI app with default settings."""
    return create_cli_app()


@pytest.fixture
def mock_download_manager(mocker, mock_queue):
    """Provide fully mocked DownloadManager with spec for type safety."""
    mock = mocker.AsyncMock(spec=DownloadManager)
    # Configure context manager behavior
    mock.__aenter__.return_value = mock
    mock.__aexit__.return_value = None
    # Configure queue attribute
    mock.queue = mock_queue
    return mock


@pytest.fixture
def mock_tracker(mocker):
    """Provide fully mocked DownloadTracker with spec."""
    mock = mocker.Mock(spec=DownloadTracker)
    return mock


@pytest.fixture
def cli_state_with_mock_manager(test_settings, mock_download_manager, mock_tracker):
    """CLIState that returns mocked manager and tracker."""

    def mock_manager_factory(**kwargs):
        return mock_download_manager

    def mock_tracker_factory(**kwargs):
        return mock_tracker

    state = CLIState(test_settings, manager_factory=mock_manager_factory)
    state.create_tracker = mock_tracker_factory
    return state


@pytest.fixture
def app_with_mock_manager(cli_state_with_mock_manager):
    """CLI app with mocked manager factory for testing."""
    return create_cli_app(state=cli_state_with_mock_manager)
