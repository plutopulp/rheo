# Benchmarks

Minimal benchmarking using `pytest-benchmark` and a local aiohttp fixture server.

## Running

- `make benchmark` — runs all benchmarks, saves JSON under `benchmarks/.results/`

## Comparing

- `make benchmark-compare` — compares all saved results in `benchmarks/.results/`

## Scenario

- `test_throughput_10_files_1mb` downloads 10 x 1MB files with 4 concurrent workers via `DownloadManager`
- Files are served locally from a background aiohttp server (`/file/{size}`) with deterministic content
- Uses `FileExistsStrategy.OVERWRITE` to ensure files are actually downloaded each iteration

## Outputs

- Results: `benchmarks/.results/` (gitignored)
- Downloads for each run: per-test `tmp_path / "downloads"` temp directory
