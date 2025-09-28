from dataclasses import dataclass


@dataclass
class FileConfig:
    """Download configuration with URL, priority, and optional metadata.

    Priority: higher numbers = higher priority (1=low, 5=high)
    Size info enables progress bars; omit if unknown.
    """

    # The URL of the file to download (required)
    url: str
    # The MIME type of the file (optional, for content validation)
    type: str | None = None
    # Human-readable description of the file (optional, for UI/logging)
    description: str | None = None
    # Priority for queue scheduling - higher numbers = higher priority (default: 1)
    priority: int = 1
    # Human-readable size estimate for display (optional)
    size_human: str | None = None
    # Exact size in bytes for progress calculation (optional)
    size_bytes: int | None = None
