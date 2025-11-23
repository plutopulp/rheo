"""Tests for DownloadManager context manager and initialization."""

import pytest
from aiohttp import ClientSession

from rheo.domain.exceptions import ManagerNotInitializedError
from rheo.downloads import (
    DownloadManager,
    DownloadWorker,
    PriorityDownloadQueue,
)


class TestDownloadManagerInitialization:
    """Test DownloadManager initialization and basic setup."""

    def test_init_with_defaults(self, mock_logger):
        """Test manager initialization with default parameters."""
        manager = DownloadManager(logger=mock_logger)

        # Should have defaults set
        assert manager.timeout is None
        assert manager.max_workers == 3
        assert isinstance(manager.queue, PriorityDownloadQueue)
        assert manager._client is None
        assert manager._worker is None
        assert not manager._owns_client

    def test_init_with_custom_params(self, mock_logger):
        """Test manager initialization with custom parameters."""
        custom_queue = PriorityDownloadQueue(logger=mock_logger)

        manager = DownloadManager(
            timeout=30.0, max_workers=5, queue=custom_queue, logger=mock_logger
        )

        assert manager.timeout == 30.0
        assert manager.max_workers == 5
        assert manager.queue is custom_queue

    def test_init_with_provided_client(self, aio_client, mock_logger):
        """Test manager initialization with provided client."""
        manager = DownloadManager(client=aio_client, logger=mock_logger)

        assert manager._client is aio_client
        assert not manager._owns_client  # We didn't create it

    def test_init_with_provided_worker(self, aio_client, mock_logger):
        """Test manager initialization with provided worker."""
        worker = DownloadWorker(aio_client, mock_logger)
        manager = DownloadManager(worker=worker, logger=mock_logger)

        assert manager._worker is worker


class TestDownloadManagerContextManager:
    """Test DownloadManager context manager behavior."""

    @pytest.mark.asyncio
    async def test_context_manager_creates_client(self, mock_logger):
        """Test that context manager creates client when none provided."""
        async with DownloadManager(logger=mock_logger) as ctx:
            # Should have created a client
            assert ctx._client is not None
            assert isinstance(ctx._client, ClientSession)
            assert ctx._owns_client

            # Should have created a worker with the client
            assert ctx._worker is not None
            assert isinstance(ctx._worker, DownloadWorker)
            assert ctx._worker.client is ctx._client

    @pytest.mark.asyncio
    async def test_context_manager_uses_provided_client(self, aio_client, mock_logger):
        """Test that context manager uses provided client."""

        async with DownloadManager(client=aio_client, logger=mock_logger) as ctx:
            # Should use provided client
            assert ctx._client is aio_client
            assert not ctx._owns_client

            # Should still create worker with provided client
            assert ctx._worker is not None
            assert ctx._worker.client is aio_client

    @pytest.mark.asyncio
    async def test_context_manager_uses_provided_worker(self, aio_client, mock_logger):
        """Test that context manager uses provided worker."""
        worker = DownloadWorker(aio_client, mock_logger)

        async with DownloadManager(
            client=aio_client, worker=worker, logger=mock_logger
        ) as ctx:
            # Should use provided worker
            assert ctx._worker is worker
            assert ctx._client is aio_client

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, mock_logger):
        """Test that context manager properly cleans up resources."""

        async with DownloadManager(logger=mock_logger) as ctx:
            client = ctx._client
            assert not client.closed

        # Client should be closed after exiting context
        assert client.closed

    @pytest.mark.asyncio
    async def test_context_manager_no_cleanup_external_client(
        self, aio_client, mock_logger
    ):
        """Test that external clients are not closed on exit."""

        async with DownloadManager(client=aio_client, logger=mock_logger):
            assert not aio_client.closed

        # External client should remain open
        assert not aio_client.closed

    @pytest.mark.asyncio
    async def test_context_manager_creates_download_directory(
        self, mock_logger, tmp_path
    ):
        """Test that context manager creates download directory if it doesn't exist."""
        download_dir = tmp_path / "nested" / "download" / "path"
        assert not download_dir.exists()

        async with DownloadManager(
            download_dir=download_dir, logger=mock_logger
        ) as manager:
            # Directory should be created
            assert download_dir.exists()
            assert download_dir.is_dir()
            assert manager.download_dir == download_dir

    @pytest.mark.asyncio
    async def test_context_manager_handles_existing_directory(
        self, mock_logger, tmp_path
    ):
        """Test that context manager handles existing directories gracefully."""
        download_dir = tmp_path / "existing"
        download_dir.mkdir()
        assert download_dir.exists()

        async with DownloadManager(
            download_dir=download_dir, logger=mock_logger
        ) as manager:
            # Directory should still exist and be usable
            assert download_dir.exists()
            assert download_dir.is_dir()
            assert manager.download_dir == download_dir


class TestDownloadManagerProperties:
    """Test DownloadManager property access and error handling."""

    def test_client_property_before_context(self, mock_logger):
        """Test accessing client property before entering context manager."""
        manager = DownloadManager(logger=mock_logger)

        with pytest.raises(ManagerNotInitializedError):
            _ = manager.client

    def test_worker_property_before_context(self, mock_logger):
        """Test accessing worker property before entering context manager."""
        manager = DownloadManager(logger=mock_logger)

        with pytest.raises(ManagerNotInitializedError):
            _ = manager.worker

    def test_client_property_with_provided_client(self, aio_client, mock_logger):
        """Test accessing client property when client was provided."""
        manager = DownloadManager(client=aio_client, logger=mock_logger)

        # Should work even before context manager
        assert manager.client is aio_client

    def test_worker_property_with_provided_worker(self, aio_client, mock_logger):
        """Test accessing worker property when worker was provided."""
        worker = DownloadWorker(aio_client, mock_logger)
        manager = DownloadManager(worker=worker, logger=mock_logger)

        # Should work even before context manager
        assert manager.worker is worker

    @pytest.mark.asyncio
    async def test_properties_after_context_entry(self, mock_logger):
        """Test that properties work correctly after entering context."""

        async with DownloadManager(logger=mock_logger) as manager:
            # Both properties should work
            client = manager.client
            worker = manager.worker

            assert isinstance(client, ClientSession)
            assert isinstance(worker, DownloadWorker)
            assert worker.client is client
