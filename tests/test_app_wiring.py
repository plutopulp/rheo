from rheo.app import App, create_app
from rheo.config.settings import Environment, LogLevel, Settings
from rheo.infrastructure.logging import get_logger, is_configured


def test_create_app_uses_default_settings():
    app = create_app()
    assert isinstance(app, App)
    assert isinstance(app.settings, Settings)
    assert app.settings.environment == Environment.PRODUCTION
    assert app.settings.log_level == LogLevel.INFO


def test_create_app_with_custom_settings(test_settings):
    """Test create_app with custom settings using fixture."""
    app = create_app(settings=test_settings)
    assert app.settings is test_settings
    assert app.settings.environment == Environment.TESTING
    assert app.settings.log_level == LogLevel.CRITICAL


def test_create_app_configures_logging():
    """Test that create_app configures logging (uses autouse fixture for clean state)."""
    assert is_configured() is False
    _ = create_app()
    assert is_configured() is True


def test_test_app_fixture_usage(test_app):
    """Test using the test_app fixture directly."""
    assert isinstance(test_app, App)
    assert test_app.settings.environment == Environment.TESTING
    assert is_configured() is True


def test_logger_configured_with_test_app(test_app):
    """Test that logger is properly configured when using test_app fixture."""
    # Logger should be configured after app creation
    assert test_app is not None
    assert is_configured() is True

    # Should be able to get logger without issues
    logger = get_logger(__name__)
    assert logger is not None

    # Should handle log calls without errors (critical level in tests)
    logger.critical("Test critical message - should appear")
    logger.info("Test info message - should be filtered out")
