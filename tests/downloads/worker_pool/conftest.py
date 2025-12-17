"""Shared fixtures for worker_pool tests."""

import typing as t
from pathlib import Path

import pytest

from rheo.domain.file_config import FileExistsStrategy
from rheo.downloads.retry.base import BaseRetryHandler
from rheo.downloads.worker.worker import DownloadWorker
from rheo.downloads.worker_pool.pool import EventSource, EventWiring, WorkerPool
from rheo.events import EventEmitter

if t.TYPE_CHECKING:
    from loguru import Logger

    from rheo.downloads.queue import PriorityDownloadQueue
    from rheo.tracking.tracker import DownloadTracker


@pytest.fixture
def make_worker_pool(
    tracker: "DownloadTracker",
    real_priority_queue: "PriorityDownloadQueue",
    mock_logger: "Logger",
    tmp_path: "Path",
) -> t.Callable[..., WorkerPool]:
    """Factory fixture to create WorkerPool instances with sensible defaults."""

    def _default_wiring() -> EventWiring:
        return {
            EventSource.QUEUE: {
                "download.queued": lambda e: tracker._track_queued(
                    e.download_id, e.url, e.priority
                ),
            },
            EventSource.WORKER: {
                "download.started": lambda e: tracker._track_started(
                    e.download_id, e.url, e.total_bytes
                ),
                "download.progress": lambda e: tracker._track_progress(
                    e.download_id, e.url, e.bytes_downloaded, e.total_bytes, e.speed
                ),
                "download.completed": lambda e: tracker._track_completed(
                    e.download_id,
                    e.url,
                    e.total_bytes,
                    e.destination_path,
                    e.validation,
                ),
                "download.failed": lambda e: tracker._track_failed(
                    e.download_id,
                    e.url,
                    Exception(f"{e.error.exc_type}: {e.error.message}"),
                    e.validation,
                ),
                "download.skipped": lambda e: tracker._track_skipped(
                    e.download_id, e.url, e.reason, e.destination_path
                ),
                "download.cancelled": lambda e: tracker._track_cancelled(
                    e.download_id, e.url
                ),
            },
        }

    def _make_pool(
        worker_factory=None,
        max_workers: int = 1,
        queue=None,
        event_wiring=None,
        file_exists_strategy: FileExistsStrategy = FileExistsStrategy.SKIP,
        retry_handler: BaseRetryHandler | None = None,
    ) -> WorkerPool:
        shared_emitter = EventEmitter(mock_logger)

        return WorkerPool(
            queue=queue or real_priority_queue,
            worker_factory=worker_factory or DownloadWorker,
            logger=mock_logger,
            download_dir=tmp_path,
            max_workers=max_workers,
            event_wiring=event_wiring or _default_wiring(),
            emitter=shared_emitter,
            file_exists_strategy=file_exists_strategy,
            retry_handler=retry_handler,
        )

    return _make_pool
