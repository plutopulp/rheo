"""Tests for DestinationResolver injection into DownloadWorker."""

import typing as t
from pathlib import Path

import pytest
from aiohttp import ClientSession
from pytest_mock import MockerFixture

from rheo.domain.file_config import FileExistsStrategy
from rheo.downloads.destination_resolver import DestinationResolver
from rheo.downloads.worker.worker import DownloadWorker

if t.TYPE_CHECKING:
    from loguru import Logger


@pytest.fixture
def mock_resolver(mocker: MockerFixture) -> DestinationResolver:
    mock = mocker.Mock(spec=DestinationResolver)
    mock.resolve.return_value = None
    return mock


class TestWorkerDestinationResolverInjection:
    """Test that worker uses injected DestinationResolver."""

    @pytest.mark.asyncio
    async def test_worker_uses_injected_policy(
        self,
        aio_client: ClientSession,
        mock_logger: "Logger",
        mock_resolver: DestinationResolver,
        tmp_path: Path,
    ) -> None:
        """Worker delegates to injected policy."""

        worker = DownloadWorker(
            client=aio_client,
            logger=mock_logger,
            destination_resolver=mock_resolver,
        )
        path = tmp_path / "file.txt"

        await worker.download(
            url="https://example.com/file.txt",
            destination_path=path,
            download_id="test-id",
        )

        mock_resolver.resolve.assert_called_once_with(
            path,
            None,
        )

    @pytest.mark.asyncio
    async def test_worker_creates_default_policy_when_none_provided(
        self,
        aio_client: ClientSession,
        mock_logger: "Logger",
    ) -> None:
        """Worker creates default DestinationResolver when none injected."""
        worker = DownloadWorker(
            client=aio_client,
            logger=mock_logger,
        )

        assert isinstance(worker._destination_resolver, DestinationResolver)
        assert worker._destination_resolver.default_strategy == FileExistsStrategy.SKIP

    @pytest.mark.asyncio
    async def test_worker_passes_strategy_override_to_policy(
        self,
        aio_client: ClientSession,
        mock_logger: "Logger",
        mock_resolver: DestinationResolver,
        tmp_path: Path,
    ) -> None:
        """Worker passes per-file strategy to policy.resolve()."""

        worker = DownloadWorker(
            client=aio_client,
            logger=mock_logger,
            destination_resolver=mock_resolver,
        )
        path = tmp_path / "file.txt"

        await worker.download(
            url="https://example.com/file.txt",
            destination_path=path,
            download_id="test-id",
            file_exists_strategy=FileExistsStrategy.OVERWRITE,
        )

        mock_resolver.resolve.assert_called_once_with(
            path,
            FileExistsStrategy.OVERWRITE,
        )
