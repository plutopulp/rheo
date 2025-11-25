"""Tests for CLI app factory and context wiring."""

from pathlib import Path

import typer

from rheo.cli.state import CLIState
from rheo.config.settings import LogLevel


class TestCLIAppFactory:
    """Test create_cli_app factory."""

    def test_returns_typer_app(self, default_app):
        """create_cli_app returns a Typer instance."""
        assert isinstance(default_app, typer.Typer)
        assert default_app.info.name == "rheo"

    def test_app_with_injected_settings(self, test_app, test_settings):
        """create_cli_app accepts settings injection for testing."""
        assert isinstance(test_app, typer.Typer)


class TestContextInjection:
    """Test our context injection and state wiring."""

    def test_commands_receive_cli_state(self, cli_runner, default_app: typer.Typer):
        """Commands receive CLIState via context."""
        captured_state = None

        @default_app.command()
        def test_cmd(ctx: typer.Context):
            nonlocal captured_state
            captured_state = ctx.obj

        result = cli_runner.invoke(default_app, ["test-cmd"])

        assert result.exit_code == 0
        assert isinstance(captured_state, CLIState)

    def test_injected_settings_available_in_context(
        self, cli_runner, test_app, test_settings
    ):
        """Injected settings are accessible in command context."""
        captured_state = None

        @test_app.command()
        def test_cmd(ctx: typer.Context):
            nonlocal captured_state
            captured_state = ctx.obj

        result = cli_runner.invoke(test_app, ["test-cmd"])

        assert result.exit_code == 0
        assert captured_state.settings.max_concurrent == test_settings.max_concurrent
        assert captured_state.settings.log_level == test_settings.log_level


class TestGlobalOptions:
    """Test global CLI flag handling."""

    def test_verbose_flag_enables_debug_logging(self, cli_runner, default_app):
        """--verbose flag sets DEBUG log level."""
        captured_state = None

        @default_app.command()
        def test_cmd(ctx: typer.Context):
            nonlocal captured_state
            captured_state = ctx.obj

        result = cli_runner.invoke(default_app, ["--verbose", "test-cmd"])

        assert result.exit_code == 0
        assert captured_state.settings.log_level == LogLevel.DEBUG

    def test_workers_flag_overrides_default(self, cli_runner, default_app):
        """--workers flag overrides max_concurrent setting."""
        captured_state = None

        @default_app.command()
        def test_cmd(ctx: typer.Context):
            nonlocal captured_state
            captured_state = ctx.obj

        result = cli_runner.invoke(default_app, ["--workers", "10", "test-cmd"])

        assert result.exit_code == 0
        assert captured_state.settings.max_concurrent == 10

    def test_download_dir_flag_overrides_default(self, cli_runner, default_app):
        """--download-dir flag overrides download directory."""
        captured_state = None

        @default_app.command()
        def test_cmd(ctx: typer.Context):
            nonlocal captured_state
            captured_state = ctx.obj

        result = cli_runner.invoke(
            default_app, ["--download-dir", "/tmp/test", "test-cmd"]
        )

        assert result.exit_code == 0
        assert captured_state.settings.download_dir == Path("/tmp/test")

    def test_injected_settings_bypass_cli_flags(
        self, cli_runner, test_app, test_settings
    ):
        """Injected settings override CLI flags (for testing)."""
        captured_state = None

        @test_app.command()
        def test_cmd(ctx: typer.Context):
            nonlocal captured_state
            captured_state = ctx.obj

        result = cli_runner.invoke(test_app, ["--workers", "99", "test-cmd"])

        assert result.exit_code == 0
        assert captured_state.settings.max_concurrent == test_settings.max_concurrent
