"""Tests for logging infrastructure."""

from async_download_manager.config.settings import Environment, LogLevel, Settings
from async_download_manager.infrastructure.logging import (
    configure_logger,
    get_logger,
    reset_logging,
    setup_logging,
)


def test_get_logger_auto_configures():
    """Test that get_logger auto-configures with defaults."""
    reset_logging()  # Clean slate

    logger = get_logger(__name__)

    # Should return a logger without raising
    assert logger is not None
    # Basic smoke test - should not raise
    logger.info("Test message")


def test_get_logger_with_explicit_setup():
    """Test get_logger after explicit setup_logging call."""
    reset_logging()

    settings = Settings(environment=Environment.TESTING, log_level="CRITICAL")
    setup_logging(settings)

    logger = get_logger(__name__)
    assert logger is not None
    logger.critical("Test critical message")


def test_configure_logger_development():
    """Test configure_logger with development environment."""
    reset_logging()

    # Should not raise
    configure_logger(level=LogLevel.DEBUG, environment=Environment.DEVELOPMENT)

    logger = get_logger(__name__)
    logger.debug("Development debug message")


def test_configure_logger_production():
    """Test configure_logger with production environment."""
    reset_logging()

    # Should not raise
    configure_logger(level=LogLevel.WARNING, environment=Environment.PRODUCTION)

    logger = get_logger(__name__)
    logger.warning("Production warning message")


def test_reset_logging():
    """Test that reset_logging cleans up configuration."""
    # Configure first
    configure_logger()
    _ = get_logger(__name__)

    # Reset
    reset_logging()

    # Should auto-configure again
    logger2 = get_logger("other_module")
    assert logger2 is not None
