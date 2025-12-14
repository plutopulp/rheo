"""Base interface for download workers."""

from abc import ABC, abstractmethod
from pathlib import Path

from ...domain.file_config import FileExistsStrategy
from ...domain.hash_validation import HashConfig
from ...domain.speed import SpeedCalculator
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

    @abstractmethod
    async def download(
        self,
        url: str,
        destination_path: Path,
        download_id: str,
        *,
        chunk_size: int = 1024,
        timeout: float | None = None,
        speed_calculator: SpeedCalculator | None = None,
        hash_config: HashConfig | None = None,
        file_exists_strategy: FileExistsStrategy | None = None,
    ) -> None:
        """Download a file from URL to local path.

        Args:
            url: HTTP/HTTPS URL to download from
            destination_path: Full path where file should be saved
            download_id: Unique identifier for this download task
            chunk_size: Size of chunks to read/write (bytes)
            timeout: HTTP request timeout in seconds
            speed_calculator: Optional speed calculator for this download
            hash_config: Optional hash validation configuration
            file_exists_strategy: Per-file override; None uses worker default

        Raises:
            Various exceptions depending on download failures.
        """
