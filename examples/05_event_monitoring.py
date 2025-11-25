#!/usr/bin/env python3
"""
05_event_monitoring.py - Real-time statistics tracking

Demonstrates:
- Aggregate statistics across all downloads
- Event-driven state updates
- Derived metrics (success rate)
- Simple one-line status display
"""

import asyncio
import typing as t
from dataclasses import dataclass
from pathlib import Path

from rheo import DownloadManager
from rheo.domain import FileConfig, HashConfig
from rheo.events import (
    DownloadCompletedEvent,
    DownloadFailedEvent,
    DownloadQueuedEvent,
    DownloadStartedEvent,
    DownloadValidationCompletedEvent,
    DownloadValidationFailedEvent,
)


def format_bytes(size: int) -> str:
    """Helper function to format bytes as human-readable."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


@dataclass
class DownloadStats:
    """Aggregate download statistics updated in real-time."""

    queued: int = 0
    in_progress: int = 0
    completed: int = 0
    failed: int = 0
    validated_success: int = 0
    validated_failed: int = 0
    total_bytes: int = 0

    @property
    def total_finished(self) -> int:
        """Total downloads that completed or failed."""
        return self.completed + self.failed

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total_finished == 0:
            return 0.0
        return (self.completed / self.total_finished) * 100

    def display(self) -> str:
        """Format stats as one-line string."""
        return (
            f"Queued: {self.queued} | In Progress: {self.in_progress} | "
            f"Completed: {self.completed} | Failed: {self.failed} | "
            f"Success: {self.success_rate:.0f}%"
        )

    def display_summary(self) -> str:
        """Return a summary of the stats as a formatted string."""
        lines = [
            "\nFinal Summary:",
            f"\tTotal Downloads: {self.queued}",
            f"\tCompleted: {self.completed}",
            f"\tFailed: {self.failed}",
            f"\tSuccess Rate: {self.success_rate:.1f}%",
            f"\tTotal Data: {format_bytes(self.total_bytes)}",
            (
                f"\tValidated: {self.validated_success} success, "
                f"{self.validated_failed} failed"
            ),
        ]
        return "\n".join(lines)


def create_event_handlers(stats: DownloadStats) -> dict[str, t.Callable]:
    """Create handlers that update aggregate statistics."""

    # Note these handlers are async for illustration purposes
    # even if sync handlers would be more appropriate here.
    # Just to show you can use either.
    async def on_queued(event: DownloadQueuedEvent) -> None:
        """Increment queued count."""
        stats.queued += 1
        print(stats.display())

    async def on_started(event: DownloadStartedEvent) -> None:
        """Increment in-progress count."""
        stats.in_progress += 1
        print(stats.display())

    async def on_completed(event: DownloadCompletedEvent) -> None:
        """Update completion stats."""
        stats.completed += 1
        stats.in_progress = max(0, stats.in_progress - 1)
        stats.total_bytes += event.total_bytes
        print(stats.display())

    async def on_failed(event: DownloadFailedEvent) -> None:
        """Update failure stats."""
        stats.failed += 1
        stats.in_progress = max(0, stats.in_progress - 1)
        print(stats.display())

    async def on_validation_completed(
        event: DownloadValidationCompletedEvent,
    ) -> None:
        """Track successful validations."""
        stats.validated_success += 1

    async def on_validation_failed(event: DownloadValidationFailedEvent) -> None:
        """Track failed validations."""
        stats.validated_failed += 1

    return {
        "tracker.queued": on_queued,
        "tracker.started": on_started,
        "tracker.completed": on_completed,
        "tracker.failed": on_failed,
        "tracker.validation_completed": on_validation_completed,
        "tracker.validation_failed": on_validation_failed,
    }


async def main() -> None:
    """Download files with real-time statistics tracking."""
    print("\nReal-time Statistics Tracking")
    print("Watch aggregate stats update after each event\n")

    files = [
        FileConfig(
            url="https://proof.ovh.net/files/10Mb.dat",
            filename="05-events-10Mb-valid.dat",
            priority=3,
            hash_config=HashConfig(
                algorithm="sha256",
                expected_hash="fb3f168caf9db959b34817a3689b8476df1852a915813936c98dd51efbdbf7db",  # noqa: E501
            ),
        ),
        FileConfig(
            url="https://proof.ovh.net/files/1Mb.dat",
            filename="05-events-1Mb-invalid.dat",
            priority=2,
            hash_config=HashConfig(
                algorithm="sha256",
                expected_hash="0" * 64,  # Intentionally wrong
            ),
        ),
        FileConfig(
            url="https://proof.ovh.net/files/10Mb.dat",
            filename="05-events-10Mb-no-hash.dat",
            priority=1,
        ),
    ]

    stats = DownloadStats()

    async with DownloadManager(
        max_concurrent=2,
        download_dir=Path("./downloads"),
    ) as manager:
        handlers = create_event_handlers(stats)

        for event_type, handler in handlers.items():
            manager.tracker.on(event_type, handler)

        # Manually trigger queued events
        for file_config in files:
            await manager.tracker.track_queued(
                str(file_config.url), file_config.priority
            )

        await manager.add(files)
        await manager.wait_until_complete()

        print(stats.display_summary())


if __name__ == "__main__":
    asyncio.run(main())
