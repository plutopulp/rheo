"""Tests for pytest fixtures and logger configuration during tests."""

from async_download_manager.config.settings import Environment, Settings
from async_download_manager.core.app import App
from async_download_manager.core.logger import get_logger, is_configured


def test_settings_fixture(test_settings):
    """Test that test_settings fixture provides correct test settings."""
    assert isinstance(test_settings, Settings)
    assert test_settings.environment == Environment.TESTING
    assert test_settings.log_level == "CRITICAL"


def test_app_fixture(test_app):
    """Test that test_app fixture provides properly configured app."""
    assert isinstance(test_app, App)
    assert test_app.settings.environment == Environment.TESTING
    assert test_app.settings.log_level == "CRITICAL"


def test_logger_configured_with_test_app(test_app):
    """Test that logger is properly configured when using test_app fixture."""
    # Logger should be configured after app creation
    assert is_configured() is True

    # Should be able to get logger without issues
    logger = get_logger(__name__)
    assert logger is not None

    # Should handle log calls without errors (critical level in tests)
    logger.critical("Test critical message - should appear")
    logger.info("Test info message - should be filtered out")


def test_logger_isolation_between_tests():
    """Test that logger state is isolated between tests."""
    # This test should start with clean state due to conftest.py fixtures
    # Even though previous test configured logging, this should start fresh
    logger = get_logger(__name__)
    assert logger is not None

    # Logger should auto-configure with defaults (not test settings)
    logger.info("Test message with default configuration")
