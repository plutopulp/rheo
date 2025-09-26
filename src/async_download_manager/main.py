from .core.app import create_app
from .core.logger import get_logger


def main():
    """Entrypoint used by CLI/tests to bootstrap the application.

    Intentionally minimal: constructs the app and returns/prints nothing.
    Higher layers (CLI or scripts) decide what to do next.
    """
    app = create_app()
    # For now, just ensure bootstrap can run without side effects.
    logger = get_logger(__name__)
    logger.info("Application bootstrapped successfully")
    return app


if __name__ == "__main__":
    main()
