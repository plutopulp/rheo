from .core.app import create_app


def main():
    """Entrypoint used by CLI/tests to bootstrap the application.

    Intentionally minimal: constructs the app and returns/prints nothing.
    Higher layers (CLI or scripts) decide what to do next.
    """
    app = create_app()
    # For now, just ensure bootstrap can run without side effects.
    print(app.settings)


if __name__ == "__main__":
    main()
