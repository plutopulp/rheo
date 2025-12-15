"""Shared fixtures for benchmarking."""

import asyncio
import threading
import typing as t
from pathlib import Path

import pytest
from aiohttp import web

_PATTERN = b"X" * 1024


async def _file_handler(request: web.Request) -> web.Response:
    """Serve deterministic content of the requested size."""
    size = int(request.match_info["size"])
    chunks, remainder = divmod(size, len(_PATTERN))
    content = _PATTERN * chunks + _PATTERN[:remainder]
    return web.Response(body=content, content_type="application/octet-stream")


class _BenchmarkServer:
    """HTTP server running in a background thread for benchmark downloads."""

    def __init__(self) -> None:
        self._base_url: str | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._runner: web.AppRunner | None = None
        self._started = threading.Event()
        self._error: BaseException | None = None

    @property
    def base_url(self) -> str:
        if self._base_url is None:
            raise RuntimeError("Server not started")
        return self._base_url

    def start(self) -> None:
        """Start the server in a background thread."""
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        self._started.wait(timeout=10)
        if self._error is not None:
            raise RuntimeError(
                f"Server failed to start: {self._error}"
            ) from self._error
        if self._base_url is None:
            raise RuntimeError("Server failed to start (timeout)")

    def stop(self) -> None:
        """Stop the server and clean up."""
        if self._loop and self._runner:
            future = asyncio.run_coroutine_threadsafe(
                self._runner.cleanup(), self._loop
            )
            future.result(timeout=5)
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)

    def _run_server(self) -> None:
        """Run the server event loop in this thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._start_server())
            self._started.set()
            self._loop.run_forever()
        except BaseException as e:
            self._error = e
            self._started.set()  # Unblock main thread so it can see the error
        finally:
            self._loop.close()

    async def _start_server(self) -> None:
        """Start the aiohttp server."""
        app = web.Application()
        app.router.add_get("/file/{size}", _file_handler)

        self._runner = web.AppRunner(app)
        await self._runner.setup()

        site = web.TCPSite(self._runner, host="127.0.0.1", port=0)
        await site.start()

        # Get the dynamically assigned port
        sockets = site._server.sockets if site._server else []
        if not sockets:
            raise RuntimeError("Failed to bind server socket")

        port = sockets[0].getsockname()[1]
        self._base_url = f"http://127.0.0.1:{port}"


@pytest.fixture(scope="session")
def benchmark_server() -> t.Iterator[str]:
    """Start an HTTP server for benchmark downloads and yield its base URL.

    The server runs in a background thread to avoid async fixture issues
    with pytest-benchmark (which uses sync test functions).
    """
    server = _BenchmarkServer()
    server.start()
    try:
        yield server.base_url
    finally:
        server.stop()


@pytest.fixture
def benchmark_download_dir(tmp_path: Path) -> Path:
    """Provide a clean download directory for each benchmark run."""
    download_dir = tmp_path / "downloads"
    download_dir.mkdir(exist_ok=True)
    return download_dir
