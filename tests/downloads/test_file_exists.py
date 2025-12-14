"""Tests for DestinationResolver."""

from pathlib import Path

import pytest

from rheo.domain.exceptions import FileExistsError
from rheo.domain.file_config import FileExistsStrategy
from rheo.downloads.destination_resolver import DestinationResolver


class TestDestinationResolver:
    """Tests for DestinationResolver.resolve()."""

    @pytest.mark.asyncio
    async def test_file_does_not_exist_returns_path(self, tmp_path: Path) -> None:
        """When file doesn't exist, returns the original path."""
        resolver = DestinationResolver()
        path = tmp_path / "new_file.txt"

        result = await resolver.resolve(path)

        assert result == path

    @pytest.mark.asyncio
    async def test_file_exists_skip_returns_none(self, tmp_path: Path) -> None:
        """When file exists and strategy is SKIP, returns None."""
        resolver = DestinationResolver(default_strategy=FileExistsStrategy.SKIP)
        path = tmp_path / "existing.txt"
        path.write_text("content")

        result = await resolver.resolve(path)

        assert result is None

    @pytest.mark.asyncio
    async def test_file_exists_overwrite_returns_path(self, tmp_path: Path) -> None:
        """When file exists and strategy is OVERWRITE, returns the path."""
        resolver = DestinationResolver(default_strategy=FileExistsStrategy.OVERWRITE)
        path = tmp_path / "existing.txt"
        path.write_text("content")

        result = await resolver.resolve(path)

        assert result == path

    @pytest.mark.asyncio
    async def test_file_exists_error_raises(self, tmp_path: Path) -> None:
        """When file exists and strategy is ERROR, raises FileExistsError."""
        resolver = DestinationResolver(default_strategy=FileExistsStrategy.ERROR)
        path = tmp_path / "existing.txt"
        path.write_text("content")

        with pytest.raises(FileExistsError):
            await resolver.resolve(path)

    @pytest.mark.asyncio
    async def test_per_file_override_takes_precedence(self, tmp_path: Path) -> None:
        """Per-file strategy override takes precedence over default."""
        resolver = DestinationResolver(default_strategy=FileExistsStrategy.SKIP)
        path = tmp_path / "existing.txt"
        path.write_text("content")

        result = await resolver.resolve(
            path, strategy_override=FileExistsStrategy.OVERWRITE
        )

        assert result == path

    @pytest.mark.asyncio
    async def test_none_override_uses_default(self, tmp_path: Path) -> None:
        """None override uses default strategy."""
        resolver = DestinationResolver(default_strategy=FileExistsStrategy.SKIP)
        path = tmp_path / "existing.txt"
        path.write_text("content")

        result = await resolver.resolve(path, strategy_override=None)

        assert result is None

    def test_default_strategy_is_skip(self) -> None:
        """Default strategy is SKIP when not specified."""
        resolver = DestinationResolver()

        assert resolver.default_strategy == FileExistsStrategy.SKIP
