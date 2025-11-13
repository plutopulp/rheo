# Ideas Bank

Collection of ideas for future development. Not commitments, just possibilities.

## Inspiration Sources

We've analysed several mature Python download managers to identify proven patterns and features:

- **pypdl**: Modern async-capable library with multi-segment focus
- **pySmartDL**: Battle-tested (29.9k users) with simple, blocking API
- **pyIDM**: GUI download manager with clipboard monitoring and scheduling
- **pyload**: Enterprise-grade (3.6k stars) with plugin system and web interface

Features below are marked with their inspiration sources where applicable. This helps us learn from proven patterns while maintaining our own architectural vision.

## 🔥 Hot Ideas

Things we're actively considering for near-term implementation.

### Multi-Segment Downloads

_Inspired by: pypdl, pySmartDL, pyIDM, pyload_

Split single files into parallel chunks for faster downloads:

- Split file into configurable segments
- Download segments concurrently
- Per-segment progress tracking
- Automatic segment merging on completion
- Adaptive chunk sizing based on file size
- Configurable max connections per file

### Hash Validation

_Inspired by: pypdl, pySmartDL_

Verify file integrity after download:

- Support MD5, SHA256, SHA512 algorithms
- Pre-download hash specification in FileConfig
- Post-download automatic verification
- FileValidator pattern for hash operations
- Optional hash mismatch handling (retry/fail)

### Speed and ETA Tracking

_Inspired by: pySmartDL_

Real-time download metrics:

- Current download speed (bytes/sec)
- Average speed calculation
- ETA estimation based on current speed
- Timestamp tracking (start/complete times)
- Per-download and aggregate statistics

### Custom Headers and Proxy Support

_Inspired by: pypdl, pyIDM, pyload_

Flexible HTTP configuration:

- Custom HTTP headers per download
- Cookie support
- HTTP/HTTPS proxy configuration
- Proxy authentication
- Per-download proxy override

### CLI Command Structure

```bash
# Core downloads
adm download <url> [--output <path>] [--workers <n>] [--priority <n>]
adm download <url> [--hash <algo>:<value>]  # With hash verification
adm download <url> [--proxy <url>]          # With proxy
adm download <url> [--segments <n>]         # Multi-segment
adm download batch <file>                   # From file
adm download batch -                        # From stdin
adm download resume <id>                    # Resume specific download
adm download retry --failed                 # Retry all failed

# Testing
adm test                            # Run default test suite
adm test --size small|medium|large  # Test by file size
adm test validate <url>             # Check if URL is downloadable

# Configuration
adm config show                     # Show all settings
adm config set <key> <value>        # Set configuration
adm config get <key>                # Get specific setting
```

### Retry Logic

- Exponential backoff with jitter
- Configurable max attempts
- Retry only on transient errors (not 404s)
- Track retry attempts in events

### Progress Display

- Rich terminal UI with live tables
- Simple progress bars with speed/ETA
- JSON output for scripts
- Quiet mode for cron jobs

## 💡 Consider

Ideas worth thinking about, but not urgent.

### Clipboard Monitoring

_Inspired by: pyIDM_

Automatically detect URLs copied to clipboard:

- Monitor system clipboard for URL patterns
- Configurable URL pattern matching (_.zip, _.pdf, etc.)
- Auto-start downloads or prompt user
- Opt-in/opt-out configuration
- Integration with system notifications

### Download Scheduling

_Inspired by: pyIDM_

Time-based download control:

- Schedule downloads for specific date/time
- Recurring schedules (daily, weekly, monthly)
- Bandwidth-aware scheduling (off-peak hours)
- Queue activation/deactivation by schedule
- Calendar-based download planning

### Mirror URLs

_Inspired by: pySmartDL, pypdl_

Fallback URL support for reliability:

- Multiple mirror URLs per download
- Automatic failover on primary URL failure
- Mirror health checking before use
- Configurable selection strategy (random, sequential, fastest)
- Load balancing across mirrors

### Auto-Resume Incomplete Downloads

_Inspired by: pyIDM, pyload_

Persistent download state management:

- Scan for .part files on startup
- Save download state to disk (JSON/SQLite)
- Auto-resume incomplete downloads
- ETag validation before resume
- Partial file cleanup on completion
- Recovery from crashes/interruptions

### Expired URL Handling

_Inspired by: pyIDM_

Handle time-limited download URLs:

- Detect expired URLs (HTTP 403/410 responses)
- URL refresh callback mechanism
- URL time-to-live (TTL) tracking
- Automatic re-fetch before retry
- Support for cloud storage signed URLs

### Package System

_Inspired by: pyload_

Group related downloads together:

- Create named download packages
- Package-level configuration and operations
- Batch add/remove/pause/resume by package
- Package metadata (name, description, tags)
- Nested package support

### Segment Size Control

_Inspired by: pypdl, pyIDM_

Fine-grained chunk configuration:

- Manual segment size specification
- Presets (auto, small, medium, large)
- Per-file connection limits
- Adaptive sizing based on file size and speed
- Minimum/maximum segment size constraints

### Synchronous API Wrapper

_Inspired by: pySmartDL_

Blocking API for simple use cases:

- Simple one-liner download function
- Synchronous DownloadManager wrapper
- get_dest() method to retrieve final path
- No async knowledge required
- Ideal for scripts and quick tasks

### Queue Management

```bash
adm queue list                      # Show queued downloads
adm queue add <url>                 # Add to persistent queue
adm queue remove <id>               # Remove from queue
adm queue pause                     # Pause processing
adm queue resume                    # Resume processing
adm queue clear                     # Clear entire queue
```

### History Tracking

```bash
adm history list [--failed] [--today] [--limit 20]
adm history show <id>               # Detailed info
adm history stats                   # Overall statistics
adm history export <file>           # Export to JSON/CSV
adm history clear                   # Clear history
```

### Authentication

```bash
adm auth add <name> --token <token>
adm auth add github --token ghp_xxx
adm auth list
adm auth remove <name>
adm download <url> --auth github
```

Support for:

- Bearer tokens
- Basic auth
- API keys
- OAuth (maybe?)

### Workspace Isolation

```bash
adm workspace create <name>
adm workspace use <name>
adm workspace list
```

Each workspace gets its own:

- Queue
- History
- Configuration
- Output directory

Use case: Separate work projects, personal downloads, etc.

### Monitoring

```bash
adm monitor                         # Live dashboard (Rich UI)
adm monitor workers                 # Worker status
adm monitor bandwidth               # Bandwidth usage
adm monitor watch <id>              # Watch specific download
```

### Bulk Operations

```bash
adm bulk import <file>              # Import JSON/YAML config
adm bulk export                     # Export all downloads
adm bulk retry --failed             # Retry all failed
adm bulk pause --all                # Pause everything
adm bulk clean --completed          # Remove completed from queue
```

## 🧊 Ice Box

Ideas we're not actively pursuing, but might revisit.

### Service Mode

_Inspired by: pyload_

Run as a background service with remote control:

- REST API with OpenAPI specification
- Daemon/headless operation mode
- Systemd service integration
- Docker deployment with multi-arch support
- Multi-user support with authentication
- Web-based administration interface

### Browser Integration

_Inspired by: pyload_

Direct integration with web browsers:

- Click 'N' Load (CNL) protocol server
- Browser extension support (Chrome, Firefox)
- FlashGot integration
- Remote download API for browser add-ons
- Automatic link capture from browser

### Link Decryption

_Inspired by: pyload_

Extract URLs from container files:

- Container file support (.dlc, .ccf, .rsdf)
- Online decrypter service integration
- Recursive link extraction
- Batch link processing
- Plugin-based decryption system

### Account Management

_Inspired by: pyload_

Manage premium file hosting accounts:

- Secure credential storage (system keyring)
- Per-hoster account configuration
- Auto-authentication before downloads
- Account status checking and validation
- Multi-account support per hoster
- Session management and persistence

### Captcha Solving

_Inspired by: pyload_

Automated captcha handling:

- Manual captcha prompt interface
- OCR-based solving integration
- Third-party solver services (anti-captcha, etc.)
- Captcha queue management
- Per-hoster captcha strategy

### Plugin System

```python
# Custom plugins for post-download actions
class VirusScanPlugin(DownloadPlugin):
    async def on_download_complete(self, context):
        await scan_file(context.file_path)

class S3UploadPlugin(DownloadPlugin):
    async def on_download_complete(self, context):
        await upload_to_s3(context.file_path, bucket)
```

### REST API

```bash
# Run as a service
adm serve --host 0.0.0.0 --port 8080

# Then use REST API
POST   /downloads          # Add download
GET    /downloads          # List downloads
GET    /downloads/:id      # Get details
DELETE /downloads/:id      # Cancel download
GET    /stats              # Get statistics
```

### Web Dashboard

Optional web interface for monitoring and control:

- Real-time download monitoring
- Add/remove downloads via UI
- Configuration management
- Download history browser

### Advanced Features

- **Smart bandwidth allocation**: Dynamically adjust per connection
- **Content-aware handling**: Auto-detect file types, decompress, etc.
- **Duplicate detection**: Check checksums before downloading
- **Smart retry**: Learn from failures, adjust strategy
- **Distributed downloads**: Coordinate across multiple machines

### Integrations

- **Cloud storage**: S3, Google Cloud Storage, Azure Blob
- **Notification systems**: Slack, Discord, email, webhooks
- **CI/CD pipelines**: GitHub Actions, GitLab CI
- **Container registries**: Docker Hub, etc.
- **Package managers**: npm, pip, cargo artifacts

### Protocol Support

Currently HTTP/HTTPS only. Could add:

- FTP/FTPS
- SFTP
- rsync
- BitTorrent (probably not)
- IPFS (interesting?)

## Anti-Patterns

Things we've explicitly decided NOT to do:

- No GUI application (CLI + Web only)
- No video streaming/transcoding
- No file hosting service
- No social features
- No blockchain anything
- Multi-user systems (complexity not worth it for library)
- Captcha solving (niche, complex, moving target)
- Account management for premium hosters (security liability)
- Full web UI (huge effort, low ROI for library-first project)

## Community Ideas

Space for community-submitted ideas (when we have a community):

- TBD

## Decision Log

Tracking major decisions:

1. **Event-based architecture**: Chose events over callbacks for flexibility
2. **Null object pattern**: Better than conditional checks everywhere
3. **Dependency injection**: Makes testing easier, more flexible
4. **Priority queue**: Simple but effective for most use cases
5. **Multi-segment downloads in Phase 1**: Proven by all 4 libraries analysed, critical for performance
6. **SQLite for persistence deferred to Phase 3**: Keep simple first, add complexity when needed
7. **Service mode moved to Ice Box**: Library-first approach, not trying to be pyload
8. **Conservative roadmap, comprehensive ideas bank**: Roadmap has proven patterns only, ideas bank captures all possibilities

## Questions to Answer

1. How to handle credentials securely? Keychain? Encrypted file?
2. SQLite or JSON for history? In-memory option?
3. Which CLI framework? Typer looks nice but adds dependency
4. How much configuration is too much?
5. Should we support config profiles?
6. Which segment size algorithm? Static vs adaptive vs user-configurable?
7. ETag validation strategy for resume? Always, optional, or automatic?
8. Mirror selection algorithm? Random, sequential, fastest-first, or load-balanced?
9. Clipboard monitoring: opt-in or opt-out by default?
