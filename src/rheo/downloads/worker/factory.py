"""Worker factory types for dependency injection."""

import typing as t

from ...domain.file_config import FileExistsStrategy
from ...events import BaseEmitter
from ...infrastructure.http import BaseHttpClient
from ..retry.base import BaseRetryHandler
from .base import BaseWorker

if t.TYPE_CHECKING:
    import loguru


class WorkerFactory(t.Protocol):
    """Factory protocol for creating worker instances.

    Any callable matching this signature can serve as a worker factory,
    including the DownloadWorker class itself, lambda functions, or custom
    factory functions.
    """

    def __call__(
        self,
        client: BaseHttpClient,
        logger: "loguru.Logger",
        emitter: BaseEmitter,
        default_file_exists_strategy: FileExistsStrategy = FileExistsStrategy.SKIP,
        retry_handler: BaseRetryHandler | None = None,
    ) -> BaseWorker:
        """Create a worker instance with the given dependencies.

        Args:
            client: HTTP client for making download requests
            logger: Logger instance for recording worker events
            emitter: Event emitter for broadcasting worker events
            default_file_exists_strategy: Default strategy for existing files
            retry_handler: Retry handler for automatic retries. None uses
                          NullRetryHandler (no retries).

        Returns:
            A BaseWorker instance ready to perform downloads
        """
        ...
