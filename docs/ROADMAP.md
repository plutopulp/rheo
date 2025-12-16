# Roadmap

What's done, what's next, and what we're considering.

## Current (Done)

The library and CLI are working for real use.

**Library:**

- Concurrent downloads with worker pool
- Priority queue system
- Selective cancellation (cancel individual downloads by ID)
- Event-driven architecture with `manager.on()`/`off()` subscription
- Download tracking and state management
- Comprehensive error handling
- Retry logic with exponential backoff
- Configurable retry policies (transient vs permanent errors)
- Speed and ETA tracking
- Hash validation (MD5, SHA256, SHA512)
- File exists handling (skip, overwrite, error)
- Full download lifecycle events (queued, started, progress, completed, failed, skipped, cancelled, retrying, validating)

**CLI:**

- Basic download command (`rheo download <url>`)
- Hash verification option
- Configuration system (env vars, .env file, CLI flags)

## Next

What we're planning to build.

**Library:**

- Multi-segment downloads (parallel chunks per file)
- Download resume support (HTTP Range requests)
- Config file support (~/.rheo/config.toml)

**CLI:**

- Batch downloads from file (`rheo download batch urls.txt`)
- Better progress UI (Rich tables and live display)
- Resume command for interrupted downloads

## Future

Things we're considering. No promises on timing or scope.

**Reliability:**

- Mirror URL support
- Bandwidth throttling (manager-level and per-download)
- Connection pooling optimisation (avoid redundant DNS lookups for same domain)

**Extensibility:**

- Post-download hooks (unzip, move, verify, chmod, etc.)
- History persistence (e.g. SQLite for download records)
- Webhook notifications

**CLI:**

- Download history commands
- Statistics and metrics display

## What We Won't Build

Things we're explicitly not building:

- BitTorrent support
- FTP/SFTP
- GUI application
- Browser extension
- Web-based UI
- Video streaming or transcoding
- File hosting service
- Multi-user systems
- Account management for file hosters
- Captcha solving
- Container/link decryption (this library is for downloading given a URL, not for extracting URLs)
- Click 'N' Load server
