import asyncio
import os

from aiohttp import ClientSession

from async_download_manager.domain.file_config import FileConfig

from .app import create_app
from .config.settings import Environment, Settings
from .downloads import DownloadWorker
from .infrastructure.logging import get_logger

FILE_CONFIG = FileConfig(
    url="https://raw.githubusercontent.com/nodejs/node/master/README.md",
    size_bytes=10_000,
    size_human="10 KB",
    type="text/markdown",
    description="Node.js README file",
    priority=1,
)


async def main():
    """Entrypoint used by CLI/tests to bootstrap the application.

    Intentionally minimal: constructs the app and returns/prints nothing.
    Higher layers (CLI or scripts) decide what to do next.
    """
    settings = Settings(environment=Environment.DEVELOPMENT, log_level="DEBUG")
    app = create_app(settings)

    logger = get_logger(__name__)
    logger.info("Application bootstrapped successfully")
    logger.info(settings)
    os.makedirs(app.settings.download_dir, exist_ok=True)

    # FileConfig knows how to generate its destination path
    file_path = FILE_CONFIG.get_destination_path(app.settings.download_dir)

    async with ClientSession() as client:
        worker = DownloadWorker(client, logger)
        await worker.download(FILE_CONFIG.url, file_path)

    return app


if __name__ == "__main__":
    asyncio.run(main())
