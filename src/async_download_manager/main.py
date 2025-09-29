import asyncio
import os

from aiohttp import ClientSession

from .config.settings import Environment, Settings
from .core.app import create_app
from .core.logger import get_logger
from .core.worker import DownloadWorker
from .test_data import get_file_config
from .utils.filename import generate_filename


async def main():
    """Entrypoint used by CLI/tests to bootstrap the application.

    Intentionally minimal: constructs the app and returns/prints nothing.
    Higher layers (CLI or scripts) decide what to do next.
    """
    settings = Settings(environment=Environment.DEVELOPMENT, log_level="DEBUG")
    app = create_app(settings)

    logger = get_logger(__name__)
    logger.info("Application bootstrapped successfully")
    os.makedirs(app.settings.download_dir, exist_ok=True)
    invalid_download_dir = app.settings.download_dir / "invalid"
    file_config = get_file_config("small_text")
    filename = generate_filename(file_config.url)
    file_path = invalid_download_dir / f"{filename}"
    async with ClientSession() as client:
        worker = DownloadWorker(client, logger)
        await worker.download(file_config.url, file_path)

    return app


if __name__ == "__main__":
    asyncio.run(main())
