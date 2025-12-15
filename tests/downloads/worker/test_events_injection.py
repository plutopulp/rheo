"""Tests for DownloadWorker event emitter dependency injection."""

import pytest

from rheo.downloads import DownloadWorker


class TestWorkerEventInjection:
    """Test that worker accepts emitter via dependency injection."""

    @pytest.mark.asyncio
    async def test_worker_accepts_emitter_in_constructor(
        self, aio_client, mock_logger, mocker
    ):
        """Test that worker can be initialised with a custom emitter."""
        mock_emitter = mocker.Mock()
        worker = DownloadWorker(aio_client, mock_logger, emitter=mock_emitter)

        assert worker.emitter is mock_emitter

    @pytest.mark.asyncio
    async def test_worker_creates_default_emitter_if_none_provided(
        self, aio_client, mock_logger
    ):
        """Test that worker creates default emitter if none provided."""
        worker = DownloadWorker(aio_client, mock_logger)

        assert hasattr(worker, "emitter")
        assert worker.emitter is not None
