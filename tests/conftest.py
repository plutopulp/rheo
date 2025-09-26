"""Pytest configuration and fixtures for async-download-manager tests."""

import pytest

from async_download_manager.config.settings import Environment, Settings
from async_download_manager.core.app import create_app
from async_download_manager.core.logger import reset_logging


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


@pytest.fixture(autouse=True)
def clean_logging_state():
    """Automatically reset logging before each test for isolation."""
    reset_logging()
    yield
    # Cleanup after test (optional, but good practice)
    reset_logging()
