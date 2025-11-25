"""Worker pool factory types for dependency injection."""

import typing as t
from pathlib import Path

from ...tracking.base import BaseTracker
from ..queue import PriorityDownloadQueue
from ..worker.factory import WorkerFactory
from .base import BaseWorkerPool

if t.TYPE_CHECKING:
    import loguru


class WorkerPoolFactory(t.Protocol):
    """Factory protocol for creating worker pool instances.

    Any callable matching this signature can serve as a worker pool factory,
    including the WorkerPool class itself, lambda functions, or custom factory
    functions.
    """

    def __call__(
        self,
        queue: PriorityDownloadQueue,
        worker_factory: WorkerFactory,
        tracker: BaseTracker,
        logger: "loguru.Logger",
        download_dir: Path,
        max_workers: int,
        **kwargs: t.Any,
    ) -> BaseWorkerPool:
        """Create a worker pool instance with the given dependencies.

        Args:
            queue: Priority queue for retrieving download tasks
            worker_factory: Factory for creating worker instances
            tracker: Download tracker for observing worker events
            logger: Logger instance for recording pool events
            download_dir: Directory where downloaded files will be saved
            max_workers: Maximum number of concurrent worker tasks
            **kwargs: Additional optional parameters (e.g., event_wiring)

        Returns:
            A BaseWorkerPool instance ready to manage workers
        """
        ...
