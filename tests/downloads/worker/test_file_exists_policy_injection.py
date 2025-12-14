"""Tests for file-exists strategy configuration in DownloadWorker."""

import typing as t

from aiohttp import ClientSession

from rheo.domain.file_config import FileExistsStrategy
from rheo.downloads.destination_resolver import DestinationResolver
from rheo.downloads.worker.worker import DownloadWorker

if t.TYPE_CHECKING:
    from loguru import Logger


class TestWorkerFileExistsStrategyConfiguration:
    """Test worker's file-exists strategy configuration."""

    def test_worker_creates_resolver_with_default_skip(
        self,
        aio_client: ClientSession,
        mock_logger: "Logger",
    ) -> None:
        """Worker creates resolver with SKIP when no strategy provided."""
        worker = DownloadWorker(
            client=aio_client,
            logger=mock_logger,
        )

        assert isinstance(worker._destination_resolver, DestinationResolver)
        assert worker._destination_resolver.default_strategy == FileExistsStrategy.SKIP

    def test_worker_creates_resolver_with_custom_strategy(
        self,
        aio_client: ClientSession,
        mock_logger: "Logger",
    ) -> None:
        """Worker creates resolver with provided default strategy."""
        worker = DownloadWorker(
            client=aio_client,
            logger=mock_logger,
            default_file_exists_strategy=FileExistsStrategy.OVERWRITE,
        )

        assert (
            worker._destination_resolver.default_strategy
            == FileExistsStrategy.OVERWRITE
        )
