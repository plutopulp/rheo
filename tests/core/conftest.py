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
    """Provide a real aiohttp ClientSession for integration testing."""
    session = ClientSession()
    yield session
    await session.close()


@pytest.fixture
def mock_aio_client(mocker):
    """Provide a mocked aiohttp ClientSession for unit tests.

    This fixture should be used for unit tests that don't need real HTTP functionality.
    For integration tests that need actual HTTP behavior (with aioresponses),
    use aio_client.
    """
    mock_client = mocker.Mock(spec=ClientSession)
    mock_client.closed = False
    return mock_client
