from dataclasses import dataclass

from .config.settings import Settings
from .infrastructure.logging import setup_logging


@dataclass(frozen=True)
class App:
    """Application wiring container.

    Holds references to cross-cutting concerns (currently only `Settings`).
    This indirection keeps configuration separate from business logic and
    makes tests easy to set up by passing explicit `Settings`.
    """

    settings: Settings


def create_app(settings: Settings | None = None) -> App:
    """Create an `App` with provided settings or defaults.

    Keep logic here minimal so boot is predictable and test-friendly.
    """
    settings = settings or Settings()
    setup_logging(settings)
    app = App(settings=settings)
    return app
