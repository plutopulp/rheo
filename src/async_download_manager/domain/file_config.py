"""File configuration and filename handling for downloads."""

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .exceptions import ValidationError

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
        filename: The filename to normalize

    Returns:
        Filename with normalized whitespace
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


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename for cross-platform filesystem compatibility.

    - Strips leading/trailing whitespace and collapses multiple spaces
    - Replaces invalid filesystem characters with underscores
    - Handles reserved Windows filenames
    - Truncates if too long (>255 chars), preserving extension

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename safe for filesystem use
    """
    filename = _normalize_whitespace(filename)
    filename = _replace_invalid_chars(filename)
    filename = _handle_windows_reserved_names(filename)
    filename = _truncate_long_filename(filename)
    return filename


def _generate_filename_from_url(url: str) -> str:
    """Generate sanitized filename from URL.

    Format: "domain-filename" or just "domain" if no path.
    Strips query parameters and fragments.

    Args:
        url: The URL to generate filename from

    Returns:
        Generated filename in format "domain-filename"

    Examples:
        >>> _generate_filename_from_url("https://example.com/path/file.txt")
        'example.com-file.txt'
        >>> _generate_filename_from_url("https://example.com/")
        'example.com'
    """
    parsed_url = urlparse(url)

    # Get domain, replacing colons in port numbers with underscores
    domain = parsed_url.netloc.replace(":", "_")

    # Get path part, strip leading/trailing slashes
    path_part = parsed_url.path.strip("/")

    if path_part:
        # Extract filename from path (last segment), remove query params
        path_part = path_part.split("/")[-1].split("?")[0]
        filename = f"{domain}-{path_part}"
    else:
        # No path, use domain only
        filename = domain

    # Sanitize the generated filename
    return _sanitize_filename(filename)


@dataclass
class FileConfig:
    """Download specification with URL, priority, and metadata.

    Priority: higher numbers = higher priority (1=low, 5=high)
    Size info enables progress bars; omit if unknown.
    """

    # ========== Required ==========
    url: str

    # ========== Metadata (for UI/logging) ==========
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

    # ========== File Management ==========
    filename: str | None = None  # Custom filename override
    destination_subdir: str | None = None  # Subdirectory within base download dir

    # ========== Download Behavior ==========
    # TODO: Implement per-file timeout override in worker.download()
    timeout: float | None = None
    # TODO: Implement retry logic in manager or worker
    max_retries: int = 0

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_url()

    def _validate_url(self) -> None:
        """Validate URL format and protocol.

        Raises:
            ValidationError: If URL is empty, missing components, or uses
            unsupported protocol
        """
        # Check for empty or whitespace-only URL
        if not self.url or not self.url.strip():
            raise ValidationError("Invalid URL: URL cannot be empty")

        parsed = urlparse(self.url)

        # Check for valid scheme and netloc
        if not all([parsed.scheme in ("http", "https"), parsed.netloc]):
            raise ValidationError(f"Invalid URL: {self.url}")

    def get_destination_filename(self) -> str:
        """Get the destination filename for this download.

        Returns the custom filename if provided, otherwise generates
        one from the URL. Result is always sanitized for filesystem safety.

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
            # Use custom filename, but sanitize it
            return _sanitize_filename(self.filename)

        # Generate from URL
        return _generate_filename_from_url(self.url)

    def get_destination_path(self, base_dir: Path, create_dirs: bool = True) -> Path:
        """Get full destination path including subdirectory.

        Combines the base directory, optional subdirectory, and filename
        to create the complete path where the file should be saved.

        Args:
            base_dir: Base download directory
            create_dirs: If True, creates parent directories if they don't
            exist (default: True)

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
            # Combine base_dir with subdirectory and filename
            # Path normalization handles trailing slashes automatically
            destination_path = base_dir / self.destination_subdir / filename

            # Create parent directories if subdirectory is specified
            if create_dirs:
                destination_path.parent.mkdir(parents=True, exist_ok=True)

            return destination_path
        else:
            # Just base_dir and filename
            return base_dir / filename
