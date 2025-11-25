"""Worker factory types for dependency injection."""

import typing as t

import aiohttp

from ...events import BaseEmitter
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
        client: aiohttp.ClientSession,
        logger: "loguru.Logger",
        emitter: BaseEmitter,
    ) -> BaseWorker:
        """Create a worker instance with the given dependencies.

        Args:
            client: HTTP session for making download requests
            logger: Logger instance for recording worker events
            emitter: Event emitter for broadcasting worker events

        Returns:
            A BaseWorker instance ready to perform downloads
        """
        ...
