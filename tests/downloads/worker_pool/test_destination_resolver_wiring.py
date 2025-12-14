"""Tests for file-exists strategy wiring through WorkerPool."""

import typing as t

from rheo.domain.file_config import FileExistsStrategy

if t.TYPE_CHECKING:
    from aiohttp import ClientSession

    from rheo.downloads.worker_pool.pool import WorkerPool


class TestWorkerPoolFileExistsStrategyWiring:
    """Ensure WorkerPool passes file-exists strategy to workers."""

    def test_pool_stores_file_exists_strategy(
        self,
        make_worker_pool: t.Callable[..., "WorkerPool"],
    ) -> None:
        """Pool stores configured file-exists strategy."""
        pool = make_worker_pool(file_exists_strategy=FileExistsStrategy.OVERWRITE)

        assert pool._file_exists_strategy == FileExistsStrategy.OVERWRITE

    def test_pool_passes_strategy_to_workers(
        self,
        aio_client: "ClientSession",
        make_worker_pool: t.Callable[..., "WorkerPool"],
    ) -> None:
        """Pool passes strategy to workers; worker creates resolver with it."""
        pool = make_worker_pool(file_exists_strategy=FileExistsStrategy.ERROR)

        worker = pool.create_worker(aio_client)

        assert worker._destination_resolver.default_strategy == FileExistsStrategy.ERROR
