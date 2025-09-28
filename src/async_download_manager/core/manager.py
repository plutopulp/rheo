from pathlib import Path

from aiohttp import ClientSession


async def download_file(
    client: ClientSession, url: str, to: Path, chunk_size: int = 1024
) -> None:
    """Download a file from a URL to a local path."""
    with open(to, "wb") as f:
        async with client.get(url) as response:
            async for chunk in response.content.iter_chunked(chunk_size):
                f.write(chunk)
