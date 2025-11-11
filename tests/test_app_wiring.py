from async_download_manager.app import App, create_app
from async_download_manager.config.settings import Environment, Settings
from async_download_manager.infrastructure.logging import is_configured


def test_create_app_uses_default_settings():
    app = create_app()
    assert isinstance(app, App)
    assert isinstance(app.settings, Settings)
    assert app.settings.environment == Environment.DEVELOPMENT
    assert isinstance(app.settings.log_level, str)


def test_create_app_with_custom_settings(test_settings):
    """Test create_app with custom settings using fixture."""
    app = create_app(settings=test_settings)
    assert app.settings is test_settings
    assert app.settings.environment == Environment.TESTING
    assert app.settings.log_level == "CRITICAL"


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
