# Roadmap

Here's where we're headed. Version 0.1.0 is done. Version 0.2.0 is what we're currently working on. Version 0.3.0 is stuff we're thinking about but not committed to yet.

## v0.1.0 (Current)

This version gets the library and CLI working well enough for real use.

**Library:**

- Concurrent downloads with worker pool
- Priority queue system
- Event-based architecture
- Download tracking and state management
- Comprehensive error handling
- Retry logic with exponential backoff
- Configurable retry policies (transient vs permanent errors)
- Speed and ETA tracking
- Hash validation (MD5, SHA256, SHA512)

**CLI:**

- Basic download command (`rheo download <url>`)
- Hash verification option
- Configuration system (env vars, .env file, CLI flags)

## v0.2.0 (Next few week)

What we're planning to build next.

**Library:**

- Multi-segment downloads (parallel chunks per file)
- Download resume support (maybe HTTP Range requests for this and item above)
- Config file support (~/.rheo/config.toml)

**CLI:**

- Batch downloads from file (`rheo download batch urls.txt`)
- Better progress UI (Rich tables and live display)
- Resume command for interrupted downloads

## v0.3.0 (Longer Term)

Things we're considering. These might happen, not definite yet.

**Reliability:**

- Mirror URL support
- Bandwidth throttling (manager-level and potentially per-download level, in tandem)
- Connection pooling optimisation (e.g. avoid redundant DNS lookup + handshakes for same domain downloads)

**Extensibility:**

- Post-download hooks (unzip, move, verify, chmod etc...). For the end user, this would be more convenient and reliable (implementation) over using events directly.
- History persistence (e.g. SQLite for download records)
- Webhook notifications

**CLI:**

- Download history commands
- Statistics and metrics display

No promises on timing or scope for this version. We'll see how v0.2.0 goes first.

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
- Container/link decryption (This library is for downloading file given a URL, not for extracting URLs from containers)
- Click 'N' Load server
