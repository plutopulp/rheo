import asyncio

from .main import main


def cli() -> None:
    asyncio.run(main())
