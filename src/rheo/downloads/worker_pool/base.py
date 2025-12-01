"""Abstract worker pool contract for download workers."""

from abc import ABC, abstractmethod

import aiohttp

from ..worker.base import BaseWorker


class BaseWorkerPool(ABC):
    """Encapsulates worker lifecycle orchestration responsibilities.

    Concrete pools manage worker creation, queue consumption loops, event
    wiring, and shutdown semantics on behalf of higher-level components such
    as `DownloadManager`.
    """

    @abstractmethod
    async def start(self, client: aiohttp.ClientSession) -> None:
        """Start worker tasks bound to the provided HTTP client.

        Implementations should spin up one asyncio Task per configured worker,
        wire event emitters to trackers prior to queue consumption, and raise if
        start is called again while the pool is running.
        """

    @abstractmethod
    async def shutdown(self, wait_for_current: bool = True) -> None:
        """Initiate shutdown while preserving queue correctness.

        When `wait_for_current` is True, workers should complete in-flight
        downloads before exiting, re-queuing any items that were dequeued but
        not yet started. When False, workers should be cancelled promptly and
        any active downloads should be interrupted.
        """

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Return True while worker tasks are active."""

    @abstractmethod
    def create_worker(self, client: "aiohttp.ClientSession") -> BaseWorker:
        """Create a fresh worker with isolated dependencies for each task."""
