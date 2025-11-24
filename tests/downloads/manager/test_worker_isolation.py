"""Test that worker tasks get isolated worker instances."""

import asyncio

import pytest

from rheo.domain.exceptions import ManagerNotInitializedError
from rheo.downloads import DownloadManager, DownloadWorker


@pytest.mark.asyncio
async def test_manager_creates_separate_worker_per_task(
    mock_aio_client, mock_logger, mock_emitter
):
    """Each worker task should have its own DownloadWorker instance.

    This prevents race conditions if mutable state is added to workers
    in the future (e.g., per-worker metrics, download counters, state flags).
    With distinct instances, each task's state remains isolated.
    Note this is an integration test at the manager level. So we use real workers.
    If we mocked the workers, we'd be testing "does the factory get called 3 times?"
    rather than "are there 3 distinct worker instances?"
    """
    created_workers = []

    def track_worker_factory(client, logger, emitter):
        worker = DownloadWorker(client, logger, emitter)
        created_workers.append(worker)
        return worker

    async with DownloadManager(
        client=mock_aio_client,
        max_workers=3,
        worker_factory=track_worker_factory,
        logger=mock_logger,
    ) as _:
        # Manager starts 3 worker tasks - give them a moment to initialize
        await asyncio.sleep(0.01)

    # Should have created 3 distinct worker instances
    assert len(created_workers) == 3
    assert (
        len(set(id(w) for w in created_workers)) == 3
    ), "Expected 3 distinct worker instances, but some were reused"


@pytest.mark.asyncio
async def test_each_worker_gets_isolated_emitter(mock_aio_client, mock_logger):
    """Verify each worker gets its own EventEmitter instance.

    True isolation requires separate emitters per worker to prevent
    event cross-contamination between concurrent downloads.
    """
    created_emitters = []

    def track_worker_factory(client, logger, emitter):
        created_emitters.append(emitter)
        return DownloadWorker(client, logger, emitter)

    async with DownloadManager(
        client=mock_aio_client,
        max_workers=3,
        worker_factory=track_worker_factory,
        logger=mock_logger,
    ):
        await asyncio.sleep(0.01)

    # Should have 3 distinct emitters
    assert len(created_emitters) == 3
    assert (
        len(set(id(e) for e in created_emitters)) == 3
    ), "Expected 3 distinct emitter instances, but some were reused"


def test_create_worker_before_initialization_raises(mock_aio_client, mock_logger):
    """_create_worker() should raise if called before manager enters context."""

    manager = DownloadManager(client=mock_aio_client, logger=mock_logger)
    # Client is provided but manager not initialized via __aenter__
    manager._client = None  # Simulate pre-init state

    with pytest.raises(ManagerNotInitializedError, match="must be initialized"):
        manager._create_worker()
