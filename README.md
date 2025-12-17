# Rheo

[![CI](https://github.com/plutopulp/rheo/workflows/CI/badge.svg)](https://github.com/plutopulp/rheo/actions)
[![codecov](https://codecov.io/gh/plutopulp/rheo/branch/main/graph/badge.svg)](https://codecov.io/gh/plutopulp/rheo)
[![PyPI](https://img.shields.io/pypi/v/rheopy)](https://pypi.org/project/rheopy/)
[![Python](https://img.shields.io/pypi/pyversions/rheopy)](https://pypi.org/project/rheopy/)
[![License](https://img.shields.io/pypi/l/rheopy)](https://github.com/plutopulp/rheo/blob/main/LICENSE)
[![Commits since release](https://img.shields.io/github/commits-since/plutopulp/rheo/latest)](https://github.com/plutopulp/rheo/compare/latest...main)

Concurrent HTTP download orchestration with async I/O

## What It Is

A Python library for managing multiple asynchronous HTTP downloads. Built on `asyncio` and `aiohttp`, it handles concurrency, tracks state, emits events, and lets you monitor progress.

## Installation

```bash
pip install rheopy
```

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

    async with DownloadManager(download_dir=Path("./downloads"), max_concurrent=3) as manager:
        await manager.add(files)
        await manager.wait_until_complete()

    print("All downloads complete!")

asyncio.run(main())
```

## Key Features

- Concurrent downloads with worker pool
- Priority queue
- Selective cancellation (cancel individual downloads by ID)
- Hash validation (MD5, SHA256, SHA512)
- Retry logic with exponential backoff
- Real-time speed & ETA tracking
- File exists handling (skip, overwrite, or error)
- Event-driven architecture with typed `DownloadEventType` and `Subscription` handles (`manager.on()` returns a handle with `unsubscribe()`)
- HTTP client abstraction (`BaseHttpClient`, default `AiohttpClient`)
- CLI tool (`rheo download`)
- Full type hints

## CLI Usage

```bash
# Basic download
rheo download https://example.com/file.zip

# With hash verification
rheo download https://example.com/file.zip --hash sha256:abc123...

# Custom output directory
rheo download https://example.com/file.zip -o /path/to/dir
```

See [CLI Reference](https://github.com/plutopulp/rheo/blob/main/docs/CLI.md) for complete command documentation.

## Documentation

- **[Full Documentation](https://github.com/plutopulp/rheo/blob/main/docs/README.md)** - Complete guide with detailed examples
- **[CLI Reference](https://github.com/plutopulp/rheo/blob/main/docs/CLI.md)** - Command-line interface
- **[Architecture](https://github.com/plutopulp/rheo/blob/main/docs/ARCHITECTURE.md)** - System design and patterns
- **[Contributing](https://github.com/plutopulp/rheo/blob/main/CONTRIBUTING.md)** - Development setup and guidelines
- **[Roadmap](https://github.com/plutopulp/rheo/blob/main/docs/ROADMAP.md)** - What's next

## Listen to Events

Subscribe to lifecycle events via `manager.on()`, which returns a `Subscription` handle:

```python
from rheo.events import DownloadEventType, DownloadCompletedEvent

def on_completed(event: DownloadCompletedEvent) -> None:
    print(f"done: {event.download_id}")

async with DownloadManager(download_dir=Path("./downloads")) as manager:
    sub = manager.on(DownloadEventType.COMPLETED, on_completed)
    await manager.add([FileConfig(url="https://example.com/file.zip")])
    await manager.wait_until_complete()
    # sub.unsubscribe() when no longer needed
```

Use `"*"` to receive all events. Type-hint your handler for autocomplete on event fields.

## Examples

Check [`examples/`](https://github.com/plutopulp/rheo/tree/main/examples) for working code:

- `01_basic_download.py` - Simple single file download
- `02_multiple_with_priority.py` - Multiple files with priorities
- `03_hash_validation.py` - File integrity verification
- `04_progress_display.py` - Real-time progress bar with speed/ETA
- `05_event_logging.py` - Lifecycle event debugging
- `06_batch_summary.py` - Batch download with summary report

## Project Status

**Alpha** - Core functionality works, but API may change before 1.0.

- Python: 3.11+
- License: MIT

## Questions?

Open an issue on [GitHub](https://github.com/plutopulp/rheo) or check the [full documentation](https://github.com/plutopulp/rheo/blob/main/docs/README.md).
