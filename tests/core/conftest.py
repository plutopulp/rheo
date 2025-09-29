import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from aiohttp import ClientSession


@pytest.fixture
def test_logger(mocker):
    """Provide a mock logger for testing that captures log calls."""
    logger = mocker.Mock()
    # Configure mock methods to avoid AttributeErrors
    logger.debug = mocker.Mock()
    logger.info = mocker.Mock()
    logger.warning = mocker.Mock()
    logger.error = mocker.Mock()
    logger.critical = mocker.Mock()
    return logger


@pytest_asyncio.fixture
async def aio_client():
    """Provide an aiohttp ClientSession for testing."""
    session = ClientSession()
    yield session
    await session.close()


@pytest.fixture
def temp_file():
    """Provide a temporary file path for download testing."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path = Path(tmp.name)
    yield path
    # Cleanup
    if path.exists():
        path.unlink()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)
