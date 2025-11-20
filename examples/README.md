# Rheo Examples

Self-contained, runnable examples demonstrating common use cases for Rheo.

## Requirements

- Python 3.12+
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

### 04_progress_tracking.py

**Demonstrates:** Real-time download monitoring with event subscriptions

**What it does:**

- Downloads a large file (100MB) with live progress tracking
- Shows real-time progress updates with percentage, speed, and ETA
- Subscribes to tracker events for real-time notifications
- Displays formatted output (human-readable bytes, speeds, time)
- Shows overall statistics at completion

**Key concepts:**

- Event subscription with `tracker.on("event_type", handler)`
- Accessing speed metrics with `tracker.get_speed_metrics(url)`
- Progress events with percentage, bytes downloaded, and total size
- Getting statistics with `tracker.get_stats()`
- Real-time monitoring patterns for building progress bars or TUIs

**Run it:**

```bash
python examples/04_progress_tracking.py
```

### 05_event_monitoring.py

**Demonstrates:** Real-time aggregate statistics tracking

**What it does:**

- Downloads 3 files with different scenarios
- Tracks aggregate statistics across all downloads
- Updates a one-line status display after each significant event
- Shows derived metrics like success rate
- Demonstrates event-driven state management

**Key concepts:**

- **Aggregate statistics** - Track counts across all downloads, not per-file
- **Simple state updates** - Each handler just increments/decrements counts
- **One-line status display** - `display()` method formats all stats
- **Event handlers:**
  - `on_queued`: Increment queued count
  - `on_started`: Increment in-progress count
  - `on_completed`: Update completion stats and total bytes
  - `on_failed`: Update failure stats
  - `on_validation_*`: Track validation success/failure
- **Complementary to example 04** - Example 04 shows per-file progress using synchronous handlers, this shows aggregate counts using async handlers.

**Run it:**

```bash
python examples/05_event_monitoring.py
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
