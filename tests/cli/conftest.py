"""Shared fixtures for CLI tests."""

import pytest
from typer.testing import CliRunner

from async_download_manager.cli.app import create_cli_app
from async_download_manager.config.settings import LogLevel, Settings


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
