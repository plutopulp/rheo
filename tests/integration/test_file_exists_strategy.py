"""Integration tests for file_exists_strategy flow."""

import typing as t
from pathlib import Path

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from rheo import DownloadManager
from rheo.domain import FileConfig, FileExistsStrategy

if t.TYPE_CHECKING:
    from loguru import Logger


class TestFileExistsStrategyIntegration:
    """Test file_exists_strategy flows from Manager through Pool to Worker."""

    @pytest.mark.asyncio
    async def test_manager_default_skip_prevents_overwrite(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Manager default SKIP should skip existing files without HTTP call."""
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("original content")

        file_config = FileConfig(
            url="https://example.com/existing.txt",
            filename="existing.txt",
        )

        with aioresponses():
            # No mock registered for this URL - would error if HTTP call made
            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
                file_exists_strategy=FileExistsStrategy.SKIP,
            ) as manager:
                await manager.add([file_config])
                await manager.wait_until_complete()

        assert existing_file.read_text() == "original content"

    @pytest.mark.asyncio
    async def test_per_file_overwrite_overrides_manager_skip(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Per-file OVERWRITE should override manager's SKIP default."""
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("original content")

        file_config = FileConfig(
            url="https://example.com/existing.txt",
            filename="existing.txt",
            file_exists_strategy=FileExistsStrategy.OVERWRITE,
        )

        with aioresponses() as mock:
            mock.get("https://example.com/existing.txt", body=b"new content")

            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
                file_exists_strategy=FileExistsStrategy.SKIP,
            ) as manager:
                await manager.add([file_config])
                await manager.wait_until_complete()

        assert existing_file.read_bytes() == b"new content"
