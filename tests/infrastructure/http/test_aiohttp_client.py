"""Tests for AiohttpClient implementation."""

import pytest
from aiohttp import ClientSession

from rheo.domain.exceptions import ClientNotInitialisedError
from rheo.infrastructure.http import AiohttpClient


class TestAiohttpClientLifecycle:
    @pytest.mark.asyncio
    async def test_creates_session_on_enter(self) -> None:
        client = AiohttpClient()
        assert client._session is None
        async with client:
            assert client._session is not None

    @pytest.mark.asyncio
    async def test_closes_session_on_exit(self) -> None:
        async with AiohttpClient() as client:
            assert not client.closed
        assert client.closed

    @pytest.mark.asyncio
    async def test_open_is_idempotent(self) -> None:
        client = AiohttpClient()
        await client.open()
        session1 = client._session
        await client.open()
        assert client._session is session1
        await client.close()

    @pytest.mark.asyncio
    async def test_uses_provided_session(self) -> None:
        provided = ClientSession()
        try:
            async with AiohttpClient(session=provided) as client:
                assert client._session is provided
        finally:
            await provided.close()

    @pytest.mark.asyncio
    async def test_does_not_close_provided_session(self) -> None:
        provided = ClientSession()
        try:
            async with AiohttpClient(session=provided):
                pass
            assert not provided.closed
        finally:
            await provided.close()


class TestAiohttpClientGet:
    @pytest.mark.asyncio
    async def test_raises_if_not_initialised(self) -> None:
        client = AiohttpClient()
        with pytest.raises(ClientNotInitialisedError, match="not initialised"):
            client.get("http://example.com")
