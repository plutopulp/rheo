#!/usr/bin/env python3
"""
07_retry_handling.py - Automatic retry with exponential backoff

Demonstrates:
- Manager-level retry handler injection
- Subscribing to RETRYING events for observability
- Custom retry policy (treating specific status codes as transient)
- Retry exhaustion behaviour

Note: This example intentionally uses failing URLs to demonstrate retry behaviour.
Requires internet connection to run.
"""

import asyncio
from datetime import datetime
from pathlib import Path

from rheo import DownloadManager
from rheo.domain import DownloadStatus, FileConfig, FileExistsStrategy
from rheo.domain.retry import RetryConfig, RetryPolicy
from rheo.downloads import RetryHandler
from rheo.events import DownloadEventType, DownloadRetryingEvent


def on_retry(event: DownloadRetryingEvent) -> None:
    """Log retry attempts with timing info."""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    short_id = event.download_id[:8] + "..."
    print(
        f"  [{ts}] Retry {event.retry}/{event.max_retries} "
        f"for {short_id} after {event.delay_seconds:.2f}s delay "
        f"(error: {event.error.exc_type})"
    )


async def example_basic_retry() -> None:
    """Basic retry handler with default policy."""
    print("=" * 70)
    print("Example 1: Basic Retry Handler")
    print("=" * 70)
    print("Using httpbin.org/status/500 (always returns 500 Internal Server Error)")
    print("Retry config: max_retries=3, base_delay=0.5s\n")

    # Create retry handler with exponential backoff
    # Default policy treats 500, 502, 503, 504 as transient (retryable)
    handler = RetryHandler(
        RetryConfig(
            max_retries=3,
            base_delay=0.5,  # Start with 0.5s delay
            max_delay=10.0,  # Cap at 10s
            jitter=False,  # Disable jitter for predictable demo output
        )
    )

    file = FileConfig(
        url="https://httpbin.org/status/500",
        filename="07-retry-basic.txt",
        destination_subdir="example_07",
    )

    async with DownloadManager(
        download_dir=Path("./downloads"),
        file_exists_strategy=FileExistsStrategy.OVERWRITE,
        retry_handler=handler,
    ) as manager:
        # Subscribe to retry events
        manager.on(DownloadEventType.RETRYING, on_retry)

        print(
            f"Starting download (will fail after {handler.config.max_retries} retries)"
        )
        await manager.add([file])
        await manager.wait_until_complete()

        # Check final status
        info = manager.get_download_info(file.id)
        if info and info.status == DownloadStatus.FAILED:
            print(f"\nDownload failed as expected: {info.error}")
        else:
            print(f"\nUnexpected status: {info.status if info else 'unknown'}")

    print()


async def example_custom_policy() -> None:
    """Custom retry policy treating 404 as transient."""
    print("=" * 70)
    print("Example 2: Custom Retry Policy")
    print("=" * 70)
    print("Using httpbin.org/status/404 (always returns 404 Not Found)")
    print("Custom policy: treating 404 as transient (normally permanent)\n")

    # Custom policy that treats 404 as retryable
    # Useful for CDNs where files may not be propagated yet
    policy = RetryPolicy(
        transient_status_codes=frozenset({404, 408, 429, 500, 502, 503, 504}),
        permanent_status_codes=frozenset({400, 401, 403, 410}),
    )

    handler = RetryHandler(
        RetryConfig(
            max_retries=2,
            base_delay=0.3,
            jitter=False,
            policy=policy,
        )
    )

    file = FileConfig(
        url="https://httpbin.org/status/404",
        filename="07-retry-custom-policy.txt",
        destination_subdir="example_07",
    )

    async with DownloadManager(
        download_dir=Path("./downloads"),
        file_exists_strategy=FileExistsStrategy.OVERWRITE,
        retry_handler=handler,
    ) as manager:
        manager.on(DownloadEventType.RETRYING, on_retry)

        print(
            f"Starting download (404 will be retried {handler.config.max_retries} times)"
        )
        await manager.add([file])
        await manager.wait_until_complete()

        info = manager.get_download_info(file.id)
        if info and info.status == DownloadStatus.FAILED:
            print(f"\nDownload failed after retries: {info.error}")

    print()


async def example_no_retry() -> None:
    """Show behaviour without retry handler (default)."""
    print("=" * 70)
    print("Example 3: No Retry Handler (Default Behaviour)")
    print("=" * 70)
    print("Using httpbin.org/status/500 without retry handler")
    print("Download will fail immediately without retrying\n")

    file = FileConfig(
        url="https://httpbin.org/status/500",
        filename="07-no-retry.txt",
        destination_subdir="example_07",
    )

    async with DownloadManager(
        download_dir=Path("./downloads"),
        file_exists_strategy=FileExistsStrategy.OVERWRITE,
        # No retry_handler - uses NullRetryHandler (no retries)
    ) as manager:
        print("Starting download (will fail immediately)...")
        await manager.add([file])
        await manager.wait_until_complete()

        info = manager.get_download_info(file.id)
        if info and info.status == DownloadStatus.FAILED:
            print(f"\nDownload failed immediately: {info.error}")

    print()


async def main() -> None:
    """Run all retry examples."""
    print("Starting retry handling examples...")
    print(
        "These examples intentionally use failing URLs to demonstrate retry behaviour\n"
    )

    await example_basic_retry()
    await example_custom_policy()
    await example_no_retry()

    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print("- Example 1: Showed exponential backoff with 3 retries")
    print("- Example 2: Showed custom policy treating 404 as transient")
    print("- Example 3: Showed immediate failure without retry handler")
    print("\nIn real usage, transient errors (network issues, 503s) would")
    print("eventually succeed after retries. These examples used always-failing")
    print("URLs to demonstrate the retry mechanism itself.")


if __name__ == "__main__":
    asyncio.run(main())
