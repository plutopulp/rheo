from dataclasses import dataclass

from ..config.settings import Settings


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
    app = App(settings=settings)
    return app
