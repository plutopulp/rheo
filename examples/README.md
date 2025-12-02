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
