"""Resolve download destinations based on file-exists strategy."""

from pathlib import Path

import aiofiles.os

from ..domain.exceptions import FileExistsError
from ..domain.file_config import FileExistsStrategy


class DestinationResolver:
    """Centralises file-exists decision logic for downloads.

    Encapsulates strategy resolution (per-file override vs default) and file
    existence checks. Returns the path to use for download, or None if the
    download should be skipped. ERROR strategy raises FileExistsError.

    Note: lives in downloads (not domain) because it performs async filesystem I/O.
    """

    def __init__(
        self,
        default_strategy: FileExistsStrategy = FileExistsStrategy.SKIP,
    ) -> None:
        """Initialise the policy with a default strategy."""
        self.default_strategy = default_strategy

    async def resolve(
        self,
        path: Path,
        strategy_override: FileExistsStrategy | None = None,
    ) -> Path | None:
        """Resolve destination path based on file existence and strategy.

        Args:
            path: Intended destination path.
            strategy_override: Per-file strategy override. If None, uses default.

        Returns:
            Path to use for download, or None if download should be skipped.

        Raises:
            FileExistsError: If file exists and effective strategy is ERROR.
        """
        strategy = strategy_override or self.default_strategy

        if not await aiofiles.os.path.exists(path):
            return path

        match strategy:
            case FileExistsStrategy.SKIP:
                return None
            case FileExistsStrategy.ERROR:
                raise FileExistsError(path)
            case FileExistsStrategy.OVERWRITE:
                return path
