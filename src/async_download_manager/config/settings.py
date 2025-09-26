from dataclasses import dataclass
from enum import Enum


class Environment(Enum):
    """Runtime environment for the application.

    Kept small and explicit to support simple environment-driven behavior
    without introducing configuration dependencies.
    """

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass(frozen=True)
class Settings:
    """Minimal settings container used to bootstrap the app.

    Rationale: keep a stable shape that core code depends on while allowing
    the app/CLI layer to decide how values are populated (env vars now,
    a config library later).
    """

    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
