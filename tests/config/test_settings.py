"""Tests for Settings configuration helpers."""

import pytest

from async_download_manager.config.settings import LogLevel, Settings, build_settings


@pytest.fixture
def default_settings():
    """Provide default Settings for comparison."""
    return Settings()


class TestBuildSettings:
    """Test our build_settings helper logic."""

    def test_filters_none_values(self, default_settings):
        """build_settings ignores None overrides."""
        settings = build_settings(
            max_workers=None,
            log_level=LogLevel.DEBUG,
        )

        assert settings.max_workers == default_settings.max_workers
        assert settings.log_level == LogLevel.DEBUG

    def test_applies_all_overrides(self):
        """build_settings applies all non-None overrides."""
        settings = build_settings(
            max_workers=10,
            log_level=LogLevel.ERROR,
            timeout=600.0,
        )

        assert settings.max_workers == 10
        assert settings.log_level == LogLevel.ERROR
        assert settings.timeout == 600.0
