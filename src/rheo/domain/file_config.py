"""File configuration and filename handling for downloads."""

import hashlib
import re
import typing as t
from enum import StrEnum
from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    computed_field,
    field_validator,
)

from .hash_validation import HashConfig


class FileExistsStrategy(StrEnum):
    """Strategy for handling existing files at download destination."""

    SKIP = "skip"  # Skip download if file exists (default)
    ERROR = "error"  # Raise FileExistsError if file exists
    OVERWRITE = "overwrite"  # Overwrite existing file
    # RENAME = "rename"  # Future: Auto-rename file.txt -> file (1).txt


# Reserved Windows filenames that need special handling
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def _replace_invalid_chars(filename: str) -> str:
    r"""Replace invalid filesystem characters with underscores.

    Invalid characters: < > : " / \ | ? *

    Args:
        filename: The filename to clean

    Returns:
        Filename with invalid characters replaced
    """
    return re.sub(r'[<>:"/\\|?*]', "_", filename)


def _normalize_whitespace(filename: str) -> str:
    """Strip leading/trailing whitespace and collapse multiple spaces.

    Args:
        filename: The filename to normalise

    Returns:
        Filename with normalised whitespace
    """
    filename = filename.strip()
    filename = re.sub(r"\s+", " ", filename)
    return filename


def _handle_windows_reserved_names(filename: str) -> str:
    """Append underscore to Windows reserved names.

    Reserved names: CON, PRN, AUX, NUL, COM1-9, LPT1-9

    Args:
        filename: The filename to check

    Returns:
        Filename with underscore appended if reserved
    """
    name_without_ext = filename.split(".")[0].upper()
    if name_without_ext in _WINDOWS_RESERVED_NAMES:
        # Append underscore to base name, preserving extension
        parts = filename.split(".", 1)
        if len(parts) == 2:
            return f"{parts[0]}_.{parts[1]}"
        else:
            return f"{filename}_"
    return filename


def _truncate_long_filename(filename: str, max_length: int = 255) -> str:
    """Truncate filename to maximum length, preserving extension.

    Args:
        filename: The filename to truncate
        max_length: Maximum allowed length (default: 255)

    Returns:
        Truncated filename
    """
    if len(filename) <= max_length:
        return filename

    # Try to preserve extension
    if "." in filename:
        name, ext = filename.rsplit(".", 1)
        # Keep extension and truncate name
        max_name_length = max_length - len(ext) - 1  # -1 for the dot
        return f"{name[:max_name_length]}.{ext}"
    else:
        return filename[:max_length]


def _sanitise_filename(filename: str) -> str:
    """Sanitise filename for cross-platform filesystem compatibility.

    - Strips leading/trailing whitespace and collapses multiple spaces
    - Replaces invalid filesystem characters with underscores
    - Handles reserved Windows filenames
    - Truncates if too long (>255 chars), preserving extension

    Args:
        filename: The filename to sanitise

    Returns:
        Sanitised filename safe for filesystem use
    """
    filename = _normalize_whitespace(filename)
    filename = _replace_invalid_chars(filename)
    filename = _handle_windows_reserved_names(filename)
    filename = _truncate_long_filename(filename)
    return filename


def _generate_filename_from_url(url: HttpUrl) -> str:
    """Generate sanitised filename from URL.

    Format: "domain-filename" or just "domain" if no path.
    Strips query parameters and fragments.
    Pydantic's HttpUrl automatically omits default ports (80/443) when
    converted to string, so we don't need to handle that manually.

    Args:
        url: The Pydantic HttpUrl to generate filename from

    Returns:
        Generated filename in format "domain-filename"

    Examples:
        >>> from pydantic import HttpUrl
        >>> _generate_filename_from_url(HttpUrl("https://example.com/path/file.txt"))
        'example.com-file.txt'
        >>> _generate_filename_from_url(HttpUrl("https://example.com/"))
        'example.com'
    """
    from urllib.parse import urlparse

    # Convert to string - Pydantic already normalised it (default ports removed)
    url_str = str(url)

    # Parse the normalised string to extract components
    parsed = urlparse(url_str)

    # Get domain (netloc won't have :443 or :80 for default ports)
    domain = parsed.netloc

    # Get path part, strip leading/trailing slashes
    path_part = parsed.path.strip("/")

    if path_part:
        # Extract filename from path (last segment), remove query params
        path_part = path_part.split("/")[-1].split("?")[0]
        filename = f"{domain}-{path_part}"
    else:
        # No path, use domain only
        filename = domain

    # Sanitise the generated filename
    return _sanitise_filename(filename)


class FileConfig(BaseModel):
    """Download specification with URL, priority, and metadata.

    Priority: higher numbers = higher priority (1=low, 5=high)
    Size info enables progress bars; omit if unknown.

    Each FileConfig automatically generates a unique ID from the URL and
    destination path, ensuring proper tracking and deduplication.
    """

    model_config = ConfigDict(frozen=True)

    # Download ID configuration
    DOWNLOAD_ID_LENGTH: t.ClassVar[int] = 16
    """Length of generated ID in hex characters.

    16 chars = 64 bits of entropy.
    Collision probability < 0.03% for 1 million downloads.
    Can be increased to 20-32 chars if higher uniqueness needed.
    """

    # ========== Required ==========
    url: HttpUrl = Field(description="HTTP/HTTPS URL to download from")

    # ========== Metadata (for UI/logging) ==========
    type: str | None = Field(
        default=None,
        description="MIME type of the file (for content validation)",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of the file",
    )
    priority: int = Field(
        default=1,
        ge=1,
        description=(
            "Queue priority - higher numbers = higher priority. "
            "Typical range: 1-5, but unbounded for flexibility."
        ),
    )
    size_human: str | None = Field(
        default=None,
        description="Human-readable size estimate for display",
    )
    size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Exact size in bytes for progress calculation",
    )

    # ========== File Management ==========
    filename: str | None = Field(
        default=None,
        description="Custom filename override",
    )
    destination_subdir: str | None = Field(
        default=None,
        description="Subdirectory within base download dir (must be relative, no '..')",
        examples=[
            "docs",
            "videos/lectures",
            "a/b/c/d/e",
        ],
    )

    # ========== Validation ==========
    hash_config: HashConfig | None = Field(
        default=None,
        description="Optional hash validation configuration",
    )

    # ========== Download Behavior ==========
    timeout: float | None = Field(
        default=None,
        gt=0,
        description="Per-file timeout override in seconds",
    )
    file_exists_strategy: FileExistsStrategy | None = Field(
        default=None,
        description="Strategy for existing files. None uses manager's default.",
    )

    @field_validator("destination_subdir")
    @classmethod
    def validate_destination_subdir(cls, v: str | None) -> str | None:
        """Validate destination_subdir is safe (no path traversal).

        Prevents security vulnerabilities by rejecting:
        - Absolute paths (e.g., "/etc")
        - Parent directory references (e.g., "..", "../../../etc")
        - Empty strings or current directory only (".", "")

        Args:
            v: The destination_subdir value to validate

        Returns:
            The validated subdirectory string

        Raises:
            ValueError: If path contains path traversal attempts or is absolute
        """
        if v is None:
            return v

        # Reject empty string or whitespace-only
        if not v.strip():
            raise ValueError("destination_subdir cannot be empty or '..'")

        subdir_path = Path(v)

        # Check 1: Reject absolute paths
        if subdir_path.is_absolute():
            raise ValueError(
                f"destination_subdir must be relative, not absolute: '{v}'"
            )

        # Check 2: Reject parent directory references
        if ".." in subdir_path.parts:
            raise ValueError(f"destination_subdir cannot contain '..': '{v}'")

        # Check 3: Reject current directory only
        if v.strip() == ".":
            raise ValueError("destination_subdir cannot be empty or '.'")

        return v

    def get_destination_filename(self) -> str:
        """Get the destination filename for this download.

        Returns the custom filename if provided, otherwise generates
        one from the URL. Result is always sanitised for filesystem safety.

        Returns:
            The filename to use for saving the downloaded file

        Examples:
            >>> config = FileConfig(url="https://example.com/file.txt")
            >>> config.get_destination_filename()
            'example.com-file.txt'
            >>> config_custom = FileConfig(url="https://example.com/file.txt",
            ... filename="my_file.txt")
            >>> config_custom.get_destination_filename()
            'my_file.txt'
        """
        if self.filename:
            # Use custom filename, but sanitise it
            return _sanitise_filename(self.filename)

        # Generate from URL
        return _generate_filename_from_url(self.url)

    def get_destination_path(self, base_dir: Path) -> Path:
        """Get full destination path including subdirectory.

        Combines the base directory, optional subdirectory, and filename
        to create the complete path where the file should be saved.

        Note: This method performs pure path computation only. Directory
        creation is the caller's responsibility (infrastructure layer).

        Args:
            base_dir: Base download directory

        Returns:
            Full path where file should be saved

        Examples:
            >>> config = FileConfig(url="https://example.com/file.txt")
            >>> config.get_destination_path(Path("/downloads"))
            PosixPath('/downloads/example.com-file.txt')
            >>> config_subdir = FileConfig(url="https://example.com/file.txt",
            ...                            destination_subdir="docs")
            >>> config_subdir.get_destination_path(Path("/downloads"))
            PosixPath('/downloads/docs/example.com-file.txt')
        """
        filename = self.get_destination_filename()

        if self.destination_subdir:
            return base_dir / self.destination_subdir / filename
        return base_dir / filename

    @computed_field  # type: ignore[prop-decorator]
    @property
    def id(self) -> str:
        """Unique identifier for this download task.

        Auto-generated from URL and relative destination path.

        Design rationale: The ID includes destination because a "download"
        represents the complete operation (fetch + save to location), not just
        content acquisition. This ensures each download task is independent,
        trackable, cancellable, and retryable without coupling.

        Used for:
        - Duplicate detection in queue (same URL+dest = duplicate)
        - Tracking downloads with same URL to different destinations
        - Event correlation across the download lifecycle

        The ID is stable: same URL + destination = same ID always.

        Future enhancements might include:
        - HTTP headers (for auth-dependent downloads)
        - HTTP method (for POST downloads)
        - Byte ranges (for partial downloads)

        Returns:
            Hex string of length DOWNLOAD_ID_LENGTH (default 16 chars = 64 bits).
            Collision probability < 0.03% for 1 million downloads.
        """
        filename = self.get_destination_filename()
        relative_path = Path(self.destination_subdir or "") / filename

        # Components that define download identity
        identity_components = [
            str(self.url),
            str(relative_path),
            # Future: str(self.headers) if self.headers else "",
            # Future: str(self.method) if self.method != "GET" else "",
        ]

        identity_string = "::".join(identity_components)
        full_hash = hashlib.sha256(identity_string.encode()).hexdigest()
        return full_hash[: self.DOWNLOAD_ID_LENGTH]
