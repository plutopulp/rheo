# Rheo Examples

Self-contained, runnable examples demonstrating common use cases for Rheo.

## Requirements

- Python 3.11+
- Rheo installed: `pip install rheopy` (or `poetry install` for development)
- **Internet connection** (examples use proof.ovh.net for testing)

## Running Examples

### Individual Examples

Run any example directly:

```bash
python examples/01_basic_download.py
```

### All Examples

Run all examples at once:

```bash
make examples
```

## Available Examples

### 01_basic_download.py

**Demonstrates:** Simplest possible download with default settings

**What it does:**

- Downloads a single 1MB test file from proof.ovh.net
- Saves to `./downloads/` directory
- Uses default settings (3 workers, no validation)

**Key concepts:**

- `DownloadManager` context manager
- `FileConfig` for URL specification
- Basic async/await pattern

**Run it:**

```bash
python examples/01_basic_download.py
```

### 02_multiple_with_priority.py

**Demonstrates:** Priority queue with concurrent downloads

**What it does:**

- Downloads 5 files with different priorities (3=high, 2=medium, 1=low)
- Shows priority ordering in action
- Uses 3 concurrent workers
- Different file sizes (1MB, 10MB, 100MB)
- Demonstrates that priority matters more than file size (small low-priority file waits)

**Key concepts:**

- Priority queue (higher numbers = higher priority)
- Concurrent downloads with worker pool
- FileConfig with priority and description parameters

**Run it:**

```bash
python examples/02_multiple_with_priority.py
```

### 03_hash_validation.py

**Demonstrates:** File integrity verification with SHA256

**What it does:**

- Shows real-world checksums workflow (how Linux ISOs, Python releases work)
- Downloads file with correct hash → validates successfully ✓
- Downloads file with wrong hash → catches mismatch ✗
- Demonstrates where checksums come from in practice
- Shows proper error handling for validation failures

**Key concepts:**

- Using `HashConfig` with SHA256 algorithm
- File integrity checking (prevents corrupted/tampered downloads)
- How checksums files work (SHA256SUMS.txt, checksums.txt)
- Hash mismatch error handling
- Real-world security practices

**Run it:**

```bash
python examples/03_hash_validation.py
```

### 04_progress_display.py

**Demonstrates:** Real-time progress bar with speed and ETA via `manager.on()`

**What it does:**

- Subscribes to `download.progress` for live updates
- Uses `SpeedMetrics` to show average speed and ETA
- Prints a simple progress bar for a 10MB download

**Key concepts:**

- Event subscription through `DownloadManager`
- Progress events with embedded speed metrics
- Basic terminal progress display

**Run it:**

```bash
python examples/04_progress_display.py
```

### 05_event_logging.py

**Demonstrates:** Wildcard event subscription and lifecycle logging

**What it does:**

- Subscribes to `"*"` to log all download events
- Prints queued → started → progress → completed with timestamps
- Shows event payload fields (priority, size, bytes, errors)

**Key concepts:**

- Wildcard event handling
- Event model introspection
- Sequential downloads for clearer logging

**Run it:**

```bash
python examples/05_event_logging.py
```

### 06_batch_summary.py

**Demonstrates:** Batch downloads with aggregate and per-file summaries

**What it does:**

- Downloads a batch of files (mix of success/failure)
- Uses `manager.stats` for totals
- Uses `manager.get_download_info()` for per-file details

**Key concepts:**

- Aggregate stats via `DownloadStats`
- Per-download status and error reporting
- Handling failures in a batch workflow

**Run it:**

```bash
python examples/06_batch_summary.py
```

### 07_retry_handling.py

**Demonstrates:** Automatic retry with exponential backoff

**What it does:**

- Shows manager-level retry handler injection
- Subscribes to `RETRYING` events for observability
- Demonstrates custom retry policy (treating 404 as transient)
- Compares behaviour with and without retry handler

**Key concepts:**

- `RetryHandler` with `RetryConfig` for retry behaviour
- `RetryPolicy` for customising which errors are transient
- Event subscription for retry observability
- Exponential backoff with configurable delays

**Note:** This example intentionally uses failing URLs (httpbin.org/status/500) to demonstrate retry exhaustion behaviour.

**Run it:**

```bash
python examples/07_retry_handling.py
```

## What to Expect

Each example will:

1. Print what it's doing
2. Download file(s) to `./downloads/` directory
3. Print completion message
4. Create files you can inspect

## Cleaning Up

To remove downloaded test files:

```bash
rm -rf ./downloads/
```

## Next Steps

Once comfortable with examples:

- Check out the [full documentation](../README.md)
- Read the [API reference](../docs/README.md)
- Try the [CLI tool](../docs/CLI.md): `rheo download <url>`
