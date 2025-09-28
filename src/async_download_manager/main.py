import asyncio
import os

from aiohttp import ClientSession

from .core.app import create_app
from .core.logger import get_logger
from .core.manager import download_file
from .test_data import get_file_config
from .utils.filename import generate_filename


async def main():
    """Entrypoint used by CLI/tests to bootstrap the application.

    Intentionally minimal: constructs the app and returns/prints nothing.
    Higher layers (CLI or scripts) decide what to do next.
    """
    app = create_app()

    logger = get_logger(__name__)
    logger.info("Application bootstrapped successfully")
    os.makedirs(app.settings.download_dir, exist_ok=True)
    file_config = get_file_config("small_text")
    filename = generate_filename(file_config.url)
    file_path = app.settings.download_dir / f"{filename}"
    async with ClientSession() as client:
        await download_file(client, file_config.url, file_path)

    return app


if __name__ == "__main__":
    asyncio.run(main())
