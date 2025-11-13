# Async Download Manager

Concurrent HTTP download manager with priority queues, progress tracking, and event-driven architecture.

## What It Is

A Python library for managing multiple asynchronous HTTP downloads. It handles concurrency, tracks state, emits events, and lets you monitor progress. Built on `asyncio` and `aiohttp`.

Think of it as a smart download queue with worker pools, where you can:

- Download multiple files simultaneously
- Prioritise certain downloads
- Track progress and state
- React to download events
- Handle errors gracefully

## Quick Start

```python
import asyncio
from pathlib import Path
from async_download_manager import DownloadManager
from async_download_manager.domain import FileConfig

async def main():
    files = [
        FileConfig(url="https://example.com/file1.zip", priority=1),
        FileConfig(url="https://example.com/file2.pdf", priority=2),
    ]

    async with DownloadManager(download_dir=Path("./downloads"), max_workers=3) as manager:
        await manager.add_to_queue(files)
        await manager.queue.join()

    print("All downloads complete!")

asyncio.run(main())
```

That's it. The manager handles worker pools, state tracking, and cleanup automatically.

## Features

- **Concurrent downloads**: Worker pool manages multiple downloads simultaneously
- **Priority queue**: Download urgent files first
- **Retry logic**: Automatic retry with exponential backoff for transient errors
- **Graceful shutdown**: Stop downloads cleanly or cancel immediately
- **Event system**: React to download lifecycle events (started, progress, completed, failed, retry)
- **Progress tracking**: Track bytes downloaded, completion status, errors
- **Async/await**: Built on asyncio for efficient I/O
- **Type hints**: Full type annotations throughout
- **Dependency injection**: Easy to test and customise
- **Resource management**: Automatic cleanup via context managers
- **Error handling**: Custom exceptions, detailed error tracking

## Installation

```bash
pip install async-download-manager
```

Or with Poetry:

```bash
poetry add async-download-manager
```

## Usage Examples

### Basic Download

```python
from async_download_manager import DownloadManager
from async_download_manager.domain import FileConfig

async with DownloadManager(download_dir=Path("./downloads")) as manager:
    await manager.add_to_queue([
        FileConfig(url="https://example.com/file.zip")
    ])
    await manager.queue.join()
```

### Priority Downloads

```python
files = [
    FileConfig(url="https://example.com/urgent.zip", priority=1),
    FileConfig(url="https://example.com/normal.pdf", priority=5),
    FileConfig(url="https://example.com/low.txt", priority=10),
]

async with DownloadManager(download_dir=Path("./downloads"), max_workers=3) as manager:
    await manager.add_to_queue(files)
    await manager.queue.join()
```

Higher priority number = downloaded first.

### Custom Filenames and Subdirectories

```python
files = [
    FileConfig(
        url="https://example.com/document.pdf",
        filename="report-2023.pdf",
        destination_subdir="reports"
    ),
    FileConfig(
        url="https://example.com/data.json",
        destination_subdir="data/raw"
    ),
]
```

### Track Progress

```python
from async_download_manager.tracking import DownloadTracker

tracker = DownloadTracker()

async with DownloadManager(
    download_dir=Path("./downloads"),
    tracker=tracker,
) as manager:
    await manager.add_to_queue(files)
    await manager.queue.join()

# Check results
for url, info in tracker.get_all_downloads().items():
    print(f"{url}: {info.status} - {info.bytes_downloaded} bytes")

stats = tracker.get_stats()
print(f"Completed: {stats.completed}, Failed: {stats.failed}")
```

### React to Events

```python
from async_download_manager.events import ChunkDownloaded

async def on_progress(event: ChunkDownloaded):
    print(f"Downloaded {event.bytes_downloaded} bytes from {event.url}")

async with DownloadManager(download_dir=Path("./downloads")) as manager:
    manager.worker.emitter.on("worker.chunk_downloaded", on_progress)
    await manager.add_to_queue(files)
    await manager.queue.join()
```

### Retry on Transient Errors

Automatic retry with exponential backoff - just provide a config:

```python
from async_download_manager.domain.retry import RetryConfig
from async_download_manager.downloads import RetryHandler, DownloadWorker

# Simple: just specify retry config (sensible defaults for everything else)
config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=60.0)
retry_handler = RetryHandler(config)

# Create worker with retry support
async with aiohttp.ClientSession() as session:
    worker = DownloadWorker(
        client=session,
        retry_handler=retry_handler,
    )
    # Worker will automatically retry transient errors (500, 503, timeouts, etc.)
    await worker.download(url, destination_path)
```

**Advanced**: Customize retry policy for specific status codes:

```python
from async_download_manager.domain.retry import RetryConfig, RetryPolicy
from async_download_manager.downloads import RetryHandler, ErrorCategoriser

# Custom policy - treat 404 as transient (normally permanent)
policy = RetryPolicy(
    transient_status_codes=frozenset({404, 408, 429, 500, 502, 503, 504}),
    permanent_status_codes=frozenset({400, 401, 403, 410}),
)
config = RetryConfig(max_retries=5, policy=policy)
retry_handler = RetryHandler(config)
```

**Note**: `RetryHandler` has sensible defaults - it automatically creates a logger, event emitter, and error categoriser if you don't provide them.

### Error Handling

```python
files = [
    FileConfig(url="https://invalid-domain.com/file.zip"),
    FileConfig(url="https://example.com/real.zip"),
]

async with DownloadManager(download_dir=Path("./downloads"), tracker=tracker) as manager:
    await manager.add_to_queue(files)
    await manager.queue.join()

# Check which failed
for url, info in tracker.get_all_downloads().items():
    if info.status == DownloadStatus.FAILED:
        print(f"Failed: {url} - {info.error}")
```

### Graceful Shutdown

Control when and how downloads stop:

```python
# Graceful shutdown - complete current downloads before stopping
async with DownloadManager(download_dir=Path("./downloads"), max_workers=3) as manager:
    await manager.add_to_queue(files)

    # Start processing...
    await asyncio.sleep(5)

    # Gracefully shut down (waits for current downloads to finish)
    await manager.shutdown(wait_for_current=True)
```

**Immediate cancellation** when you need to stop right away:

```python
# Immediate shutdown - cancel all downloads immediately
async with DownloadManager(download_dir=Path("./downloads")) as manager:
    await manager.add_to_queue(large_file_list)

    # Start processing...
    await asyncio.sleep(2)

    # Stop immediately without waiting
    await manager.shutdown(wait_for_current=False)
```

**Note**: The context manager (`async with`) automatically triggers graceful shutdown on exit, so explicit `shutdown()` calls are only needed for early termination.

## Project Status

**Alpha/Early Development**: The core library works, but we're still adding features. API might change before 1.0.

Recently completed:

- ✅ Retry logic with exponential backoff
- ✅ Configurable retry policies
- ✅ Smart error categorization (transient vs permanent)
- ✅ Graceful shutdown with configurable behavior

Current focus:

- Download resume support (HTTP Range requests)
- Multi-segment parallel downloads
- CLI interface

See `docs/ROADMAP.md` for details.

## Development

### Setup

```bash
git clone https://github.com/yourusername/async-downloader.git
cd async-downloader
poetry install
```

### Run Tests

```bash
poetry run pytest
```

### Run Demo

```bash
poetry run python -m src.async_download_manager.main
```

## Architecture

The library is organised into bounded contexts:

- **Domain**: Core models (`FileConfig`, `DownloadInfo`, `DownloadStatus`)
- **Downloads**: Queue, manager, and worker implementations
- **Events**: Event system and typed event models
- **Tracking**: State tracking and statistics
- **Infrastructure**: Logging, HTTP client setup

See `docs/ARCHITECTURE.md` for detailed design decisions.

## Contributing

Contributions are welcome! Please:

1. Check `docs/ROADMAP.md` to see what we're working on
2. Open an issue to discuss before major changes
3. Write tests for new features
4. Follow existing code style
5. Update docs if needed

## Licence

MIT Licence - see LICENSE file for details.

## Links

- Documentation: `docs/`
- Roadmap: `docs/ROADMAP.md`
- Ideas: `docs/IDEAS.md`
- Architecture: `docs/ARCHITECTURE.md`

## Questions?

Open an issue on GitHub or check the docs. The code is structured to be readable - when in doubt, look at the tests for usage examples.
