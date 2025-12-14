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

    @pytest.mark.asyncio
    async def test_manager_overwrite_applies_to_multiple_files(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Manager OVERWRITE strategy should apply to all files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("original 1")
        file2.write_text("original 2")

        configs = [
            FileConfig(url="https://example.com/file1.txt", filename="file1.txt"),
            FileConfig(url="https://example.com/file2.txt", filename="file2.txt"),
        ]

        with aioresponses() as mock:
            mock.get("https://example.com/file1.txt", body=b"new 1")
            mock.get("https://example.com/file2.txt", body=b"new 2")

            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
                file_exists_strategy=FileExistsStrategy.OVERWRITE,
            ) as manager:
                await manager.add(configs)
                await manager.wait_until_complete()

        assert file1.read_bytes() == b"new 1"
        assert file2.read_bytes() == b"new 2"

    @pytest.mark.asyncio
    async def test_manager_error_prevents_overwrite_of_existing_file(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Manager ERROR strategy should prevent overwriting existing files.

        Note: ERROR strategy raises FileExistsError which is caught by pool.
        The file is not modified and no HTTP call is made. Currently the pool
        logs the error but doesn't emit download.failed - this may change.
        """
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("original content")

        file_config = FileConfig(
            url="https://example.com/existing.txt",
            filename="existing.txt",
        )

        with aioresponses():
            # No mock needed - should fail before HTTP call
            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
                file_exists_strategy=FileExistsStrategy.ERROR,
            ) as manager:
                await manager.add([file_config])
                await manager.wait_until_complete()

                # Download did not complete
                stats = manager.stats
                assert stats.completed == 0

        # Original file unchanged - ERROR strategy prevented overwrite
        assert existing_file.read_text() == "original content"
        # Verify the error was logged
        mock_logger.error.assert_called_once()
        error_message = mock_logger.error.call_args[0][0]
        assert "FileExistsError" in error_message
