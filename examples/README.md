# Rheo Examples

Self-contained, runnable examples demonstrating common use cases for Rheo.

## Requirements

- Python 3.12+
- Rheo installed: `pip install rheopy` (or `poetry install` for development)
- **Internet connection** (examples use httpbin.org for testing)

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

- Downloads a single 1KB test file from httpbin.org
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
