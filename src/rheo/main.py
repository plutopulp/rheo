import asyncio
import os
from pathlib import Path

from pydantic import HttpUrl

from rheo.domain.file_config import FileConfig

from .app import App, create_app
from .config.settings import Environment, LogLevel, Settings
from .downloads import DownloadManager
from .infrastructure.logging import get_logger

# Import test files for demo (dynamic import to avoid test dependency in production)
try:
    from tests.fixtures.test_data import TEST_FILES
except ImportError:
    TEST_FILES = {}


async def main() -> App:
    """Demo script showcasing DownloadManager capabilities.

    Demonstrates:
    - Priority queue management with multiple files
    - Concurrent downloads with worker pool (3 workers)
    - Hash validation for file integrity
    - Mixed success/failure scenarios with error handling
    - Basic statistics reporting

    Downloads 7-8 files of varying priorities and includes intentionally
    failing URLs to demonstrate robust error handling.
    """
    settings = Settings(environment=Environment.DEVELOPMENT, log_level=LogLevel.DEBUG)
    app = create_app(settings)

    logger = get_logger(__name__)
    logger.info("Application bootstrapped successfully")
    logger.info(settings)
    os.makedirs(app.settings.download_dir, exist_ok=True)

    # Select diverse files for demo: small and medium files with varied priorities
    demo_files = [
        TEST_FILES.get("small_text"),
        TEST_FILES.get("small_json"),
        TEST_FILES.get("small_image"),
        TEST_FILES.get("medium_binary"),
        TEST_FILES.get("medium_image"),
        TEST_FILES.get("medium_zip"),
        # Add file with hash validation to demonstrate integrity checking
        # Note: This will fail validation unless you provide a correct hash
        # To use validation, download the file first, calculate its hash, then add
        # it here
        # Example: echo -n $(shasum -a 256 1Mb.dat | cut -d' ' -f1)
        # FileConfig(
        #     url=HttpUrl("https://proof.ovh.net/files/1Mb.dat"),
        #     description="1MB test file (with SHA256 validation)",
        #     priority=1,
        #     hash_config=HashConfig(
        #         algorithm=HashAlgorithm.SHA256,
        #         expected_hash="<insert-correct-hash-here>",
        #     ),
        # ),
        # Add intentionally failing URLs to demonstrate error handling
        FileConfig(
            url=HttpUrl(
                "https://invalid-domain-that-does-not-exist-12345.com/file.txt"
            ),
            description="Invalid URL (should fail)",
            priority=2,
        ),
        FileConfig(
            url=HttpUrl("https://httpstat.us/404"),
            description="404 Not Found (should fail)",
            priority=3,
        ),
    ]

    # Filter out None values and create list
    file_configs = [f for f in demo_files if f is not None]

    logger.info(f"Added {len(file_configs)} files to download queue")
    logger.info("Starting 3 concurrent workers...")

    # Track results
    successful_downloads: list[tuple[str, Path]] = []
    failed_downloads: list[tuple[str, str]] = []

    async with DownloadManager(
        download_dir=Path(app.settings.download_dir),
        max_concurrent=3,
        logger=logger,
    ) as manager:
        # Add files to priority queue
        await manager.add(file_configs)

        # Wait for queue to complete
        # Note: In production, you'd want better error handling per-file
        # For demo purposes, we'll let the queue process and report summary
        try:
            await manager.queue.join()
        except Exception as e:
            logger.error(f"Queue processing encountered errors: {e}")

    # Collect results by checking which files were downloaded
    download_dir_path = Path(app.settings.download_dir)
    for file_config in file_configs:
        try:
            expected_path = file_config.get_destination_path(download_dir_path)
            if expected_path.exists():
                successful_downloads.append(
                    (file_config.description or str(file_config.url), expected_path)
                )
            else:
                failed_downloads.append(
                    (
                        file_config.description or str(file_config.url),
                        "File not created",
                    )
                )
        except Exception as e:
            failed_downloads.append(
                (file_config.description or str(file_config.url), str(e))
            )

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("Download Summary:")
    logger.info(f"  ✓ {len(successful_downloads)} successful downloads")
    logger.info(f"  ✗ {len(failed_downloads)} failed downloads")
    logger.info(f"  📁 Files saved to: {app.settings.download_dir}")
    logger.info("=" * 60)

    if successful_downloads:
        logger.info("\nSuccessful downloads:")
        for desc, path in successful_downloads:
            logger.info(f"  ✓ {desc}")
            logger.info(f"    → {path.name}")

    if failed_downloads:
        logger.info("\nFailed downloads:")
        for desc, reason in failed_downloads:
            logger.info(f"  ✗ {desc}")
            logger.info(f"    → {reason}")

    return app


if __name__ == "__main__":
    asyncio.run(main())
