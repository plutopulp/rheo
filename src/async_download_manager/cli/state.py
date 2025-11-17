"""CLI state container."""

from ..config.settings import Settings


class CLIState:
    """Application state container for CLI commands.

    Holds Settings and can be extended with other shared state
    (e.g., TrackerFactory, ManagerFactory) as CLI grows.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
