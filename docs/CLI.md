# `rheo`

Rheo - Concurrent HTTP download orchestration with async I/O

**Usage**:

```console
$ rheo [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `-d, --download-dir PATH`: Directory to save downloads
* `-w, --workers INTEGER RANGE`: Number of concurrent workers  [x&gt;=1]
* `-v, --verbose`: Enable verbose output (DEBUG logging)
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `download`: Download a file from a URL.

## `rheo download`

Download a file from a URL.

Examples:
    rheo download https://example.com/file.zip
    rheo download https://example.com/file.zip -o /path/to/dir
    rheo download https://example.com/file.zip --filename custom.zip
    rheo download https://example.com/file.zip --hash sha256:abc123...

**Usage**:

```console
$ rheo download [OPTIONS] URL
```

**Arguments**:

* `URL`: URL to download  [required]

**Options**:

* `-o, --output PATH`: Output directory
* `--filename TEXT`: Custom filename
* `--hash TEXT`: Hash for validation (format: algorithm:hash)
* `--help`: Show this message and exit.
