# Rheo - Complete Documentation

> **Quick start?** See the [root README](../README.md) for installation and basic usage.

This is the comprehensive documentation with detailed examples and advanced usage.

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
from rheo import DownloadManager
from rheo.domain import FileConfig

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

- **Command-line interface**: Simple `rheo download` command with progress display and hash validation
- **Concurrent downloads**: Worker pool manages multiple downloads simultaneously
- **Priority queue**: Download urgent files first
- **Hash validation**: Verify file integrity with MD5, SHA256, or SHA512 checksums
- **Retry logic**: Automatic retry with exponential backoff for transient errors
- **Speed & ETA tracking**: Real-time download speed with moving averages and estimated completion time
- **Graceful shutdown**: Stop downloads cleanly or cancel immediately
- **Event system**: React to download lifecycle events (started, progress, speed, completed, failed, retry, validation)
- **Progress tracking**: Track bytes downloaded, completion status, errors, validation state, and final average speeds
- **Async/await**: Built on asyncio for efficient I/O
- **Type hints**: Full type annotations throughout
- **Dependency injection**: Easy to test and customise
- **Resource management**: Automatic cleanup via context managers
- **Error handling**: Custom exceptions, detailed error tracking

## Installation

```bash
pip install rheopy
```

Or with Poetry:

```bash
poetry add rheopy
```

## CLI Usage

The package includes a `rheo` command-line tool for quick downloads:

### Basic Download

```bash
rheo download https://example.com/file.zip
```

### Custom Output Directory

```bash
rheo download https://example.com/file.zip -o /path/to/dir
```

### Custom Filename

```bash
rheo download https://example.com/file.zip --filename custom-name.zip
```

### Hash Verification

```bash
rheo download https://example.com/file.zip --hash sha256:abc123...
```

### Global Options

```bash
# Verbose logging
rheo --verbose download https://example.com/file.zip

# Custom worker count
rheo --workers 5 download https://example.com/file.zip

# Custom download directory for all commands
rheo --download-dir /tmp/downloads download https://example.com/file.zip
```

### Configuration

Settings can be configured via:

1. **CLI flags** (highest priority): `--workers`, `--download-dir`, `--verbose`
2. **Environment variables**: `RHEO_DOWNLOAD_DIR`, `RHEO_MAX_WORKERS`, `RHEO_LOG_LEVEL`
3. **`.env` file** in current directory
4. **Defaults** (lowest priority)

Example `.env` file:

```bash
RHEO_DOWNLOAD_DIR=/home/user/downloads
RHEO_MAX_WORKERS=3
RHEO_LOG_LEVEL=INFO
RHEO_TIMEOUT=300.0
```

## Library Usage Examples

### Basic Library Usage

```python
from rheo import DownloadManager
from rheo.domain import FileConfig

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
from rheo.tracking import DownloadTracker

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

### Monitor Download Speed & ETA

Track real-time download speeds and get completion estimates:

```python
from rheo.tracking import DownloadTracker

tracker = DownloadTracker()

async with DownloadManager(
    download_dir=Path("./downloads"),
    tracker=tracker,
) as manager:
    await manager.add_to_queue(files)

    # Query speed metrics while download is active
    await asyncio.sleep(2)  # Let downloads start

    for url in files:
        metrics = tracker.get_speed_metrics(url.url)
        if metrics:
            print(f"{url.url}:")
            print(f"  Current: {metrics.current_speed_bps / 1024:.2f} KB/s")
            print(f"  Average: {metrics.average_speed_bps / 1024:.2f} KB/s")
            print(f"  ETA: {metrics.eta_seconds:.1f}s" if metrics.eta_seconds else "  ETA: Unknown")

    await manager.queue.join()

    # After completion, average speed is persisted in DownloadInfo
    for url, info in tracker.get_all_downloads().items():
        if info.average_speed_bps:
            print(f"{url}: {info.average_speed_bps / 1024:.2f} KB/s average")
```

**Key features**:

- **Instantaneous speed**: Current chunk speed (reacts quickly to changes)
- **Moving average**: Smoothed speed over configurable window (default 5s)
- **ETA**: Estimated time to completion based on average speed
- **Historical data**: Final average speed persisted for completed/failed downloads

### React to Events

```python
from rheo.events import WorkerProgressEvent, WorkerSpeedUpdatedEvent

async def on_progress(event: WorkerProgressEvent):
    print(f"Downloaded {event.bytes_downloaded} bytes from {event.url}")

async def on_speed_update(event: WorkerSpeedUpdatedEvent):
    print(f"{event.url}: {event.average_speed_bps / 1024:.2f} KB/s, ETA: {event.eta_seconds:.1f}s")

async with DownloadManager(download_dir=Path("./downloads")) as manager:
    manager.worker.emitter.on("worker.progress", on_progress)
    manager.worker.emitter.on("worker.speed_updated", on_speed_update)
    await manager.add_to_queue(files)
    await manager.queue.join()
```

### Hash Validation

Verify file integrity with cryptographic hashes to ensure downloads aren't corrupted:

```python
from rheo.domain import FileConfig, HashConfig
from rheo.domain.hash_validation import HashAlgorithm

# Single file with hash validation
files = [
    FileConfig(
        url="https://example.com/important-file.zip",
        hash_config=HashConfig(
            algorithm=HashAlgorithm.SHA256,
            expected_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
    )
]

async with DownloadManager(download_dir=Path("./downloads")) as manager:
    await manager.add_to_queue(files)
    await manager.queue.join()
# Download succeeds only if hash matches, otherwise raises HashMismatchError
```

**Convenient checksum string format**:

```python
# Use the shorthand "algorithm:hash" format
file_config = FileConfig(
    url="https://example.com/file.tar.gz",
    hash_config=HashConfig.from_checksum_string("sha256:abc123...")
)
```

**Supported algorithms**: MD5, SHA256, SHA512

**How it works**:

- Hash is calculated after download completes
- Uses streaming validation (memory-efficient for large files)
- Runs in thread pool to avoid blocking event loop
- Uses constant-time comparison to prevent timing attacks
- Failed validation deletes corrupted file and raises `HashMismatchError`
- Emits validation events: `validation_started`, `validation_completed`, `validation_failed`

**Track validation state**:

```python
tracker = DownloadTracker()

async with DownloadManager(download_dir=Path("./downloads"), tracker=tracker) as manager:
    await manager.add_to_queue(files)
    await manager.queue.join()

# Check validation results
for url, info in tracker.get_all_downloads().items():
    if info.validation:
        print(f"{url}: {info.validation.status}")
        if info.validation.status == "succeeded":
            print(f"  Hash: {info.validation.calculated_hash}")
        elif info.validation.status == "failed":
            print(f"  Error: {info.validation.error_message}")
```

### Retry on Transient Errors

Automatic retry with exponential backoff - just provide a config:

```python
from rheo.domain.retry import RetryConfig
from rheo.downloads import RetryHandler, DownloadWorker

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
from rheo.domain.retry import RetryConfig, RetryPolicy
from rheo.downloads import RetryHandler, ErrorCategoriser

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

## Security Considerations

### Path Traversal Protection

`FileConfig.destination_subdir` is automatically validated to prevent path traversal attacks. The following are rejected:

- **Parent directory references**: `".."`, `"../etc"`, `"docs/../../etc"`
- **Absolute paths**: `"/etc"`, `"/home/user"`
- **Empty or current directory**: `""`, `"."`

```python
# ✅ Valid - relative subdirectories
FileConfig(url="...", destination_subdir="videos/lectures")

# ❌ Rejected - path traversal attempt
FileConfig(url="...", destination_subdir="../../../etc")
# Raises: ValidationError: destination_subdir cannot contain '..'
```

### Best Practices

- **Validate URLs**: When accepting URLs from untrusted sources, validate them before creating `FileConfig`
- **Restrict download directories**: Use dedicated download directories with appropriate filesystem permissions
- **Hash validation**: Use `hash_config` parameter to verify file integrity when checksums are available
- **Monitor events**: Subscribe to download events to detect and respond to suspicious activity

## Project Status

**Alpha/Early Development**: The core library works, but we're still adding features. API might change before 1.0.

Recently completed:

- ✅ Retry logic with exponential backoff
- ✅ Configurable retry policies
- ✅ Smart error categorization (transient vs permanent)
- ✅ Graceful shutdown with configurable behavior
- ✅ Real-time speed and ETA tracking
- ✅ Hash validation (MD5, SHA256, SHA512)
- ✅ CLI interface with progress display

Current focus:

- Download resume support (HTTP Range requests)
- Multi-segment parallel downloads
- Custom HTTP headers and authentication
- Enhanced CLI features (batch downloads, Rich UI progress)

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
poetry run python -m src.rheo.main
```

## Architecture

The library is organised into bounded contexts:

- **Domain**: Core models (`FileConfig`, `DownloadInfo`, `DownloadStatus`, `HashConfig`, `ValidationState`, `SpeedMetrics`, `SpeedCalculator`)
- **Downloads**: Queue, manager, worker, and file validation implementations
- **Events**: Event system and typed event models (including speed and validation events)
- **Tracking**: State tracking, statistics, real-time speed metrics, and validation state
- **Infrastructure**: Logging, HTTP client setup
- **CLI**: Command-line interface with Typer, event-driven display, and configuration management

See `docs/ARCHITECTURE.md` for detailed design decisions.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup, code quality guidelines, and PR process.

## Licence

MIT Licence - see LICENSE file for details.

## Documentation

- **[CLI Reference](docs/CLI.md)** - Complete command-line interface documentation
- **[Architecture](docs/ARCHITECTURE.md)** - System design and component overview
- **[Roadmap](docs/ROADMAP.md)** - Feature roadmap and development phases
- **[Ideas](docs/IDEAS.md)** - Future ideas and brainstorming

## Questions?

Open an issue on GitHub or check the docs. The code is structured to be readable - when in doubt, look at the tests for usage examples.
