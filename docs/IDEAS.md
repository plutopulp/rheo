# Ideas Bank

Collection of ideas for future development. Not commitments, just possibilities.

## 🔥 Hot Ideas

Things we're actively considering for near-term implementation.

### CLI Command Structure

```bash
# Core downloads
adm download <url> [--output <path>] [--workers <n>] [--priority <n>]
adm download batch <file>           # From file
adm download batch -                # From stdin
adm download resume <id>            # Resume specific download
adm download retry --failed         # Retry all failed

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
- Simple progress bars
- JSON output for scripts
- Quiet mode for cron jobs

## 💡 Consider

Ideas worth thinking about, but not urgent.

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

- **Parallel chunk downloads**: Split single file into chunks, download in parallel
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
- No browser integration
- No video streaming/transcoding
- No file hosting service
- No social features
- No blockchain anything

## Community Ideas

Space for community-submitted ideas (when we have a community):

- TBD

## Decision Log

Tracking major decisions:

1. **Event-based architecture**: Chose events over callbacks for flexibility
2. **Null object pattern**: Better than conditional checks everywhere
3. **Dependency injection**: Makes testing easier, more flexible
4. **Priority queue**: Simple but effective for most use cases

## Questions to Answer

1. How to handle credentials securely? Keychain? Encrypted file?
2. SQLite or JSON for history? In-memory option?
3. Which CLI framework? Typer looks nice but adds dependency
4. How much configuration is too much?
5. Should we support config profiles?
