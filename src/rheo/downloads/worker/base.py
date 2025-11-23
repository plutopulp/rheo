"""Base interface for download workers."""

from abc import ABC, abstractmethod

from ...domain.file_config import FileConfig
from ...events import BaseEmitter


class BaseWorker(ABC):
    """Abstract base class for download worker implementations.

    Defines the interface for workers that handle file downloads.
    Different implementations can provide different download strategies
    (e.g., single-stream, multi-segment).
    """

    @property
    @abstractmethod
    def emitter(self) -> BaseEmitter:
        """Event emitter for broadcasting worker events.

        The manager wires events from this emitter to trackers.
        All workers must expose their emitter for event wiring.
        """
        pass

    @abstractmethod
    async def download(self, file_config: FileConfig) -> None:
        """Download a file according to the configuration.

        Args:
            file_config: Configuration specifying URL, destination,
                        hash validation, priority, etc.

        Raises:
            Various exceptions depending on download failures.
        """
        pass
