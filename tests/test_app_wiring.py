from async_download_manager.config.settings import Environment, Settings
from async_download_manager.core.app import App, create_app


def test_create_app_uses_default_settings():
    app = create_app()
    assert isinstance(app, App)
    assert isinstance(app.settings, Settings)
    assert app.settings.environment == Environment.DEVELOPMENT
    assert isinstance(app.settings.log_level, str)


def test_create_app_with_custom_settings():
    custom = Settings(environment=Environment.TESTING, log_level="CRITICAL")
    app = create_app(settings=custom)
    assert app.settings is custom
