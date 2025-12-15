"""Tests for HTTP factory functions."""

import ssl

import aiohttp
import pytest

from rheo.infrastructure.http import create_secure_connector, create_ssl_context


class TestCreateSslContext:
    def test_returns_ssl_context(self) -> None:
        ctx = create_ssl_context()
        assert isinstance(ctx, ssl.SSLContext)

    def test_uses_certifi_ca_bundle(self) -> None:
        ctx = create_ssl_context()
        # Context should have CA certs loaded (non-empty)
        assert ctx.cert_store_stats()["x509_ca"] > 0


class TestCreateSecureConnector:
    @pytest.mark.asyncio
    async def test_returns_tcp_connector(self) -> None:
        connector = create_secure_connector()
        assert isinstance(connector, aiohttp.TCPConnector)

    @pytest.mark.asyncio
    async def test_accepts_custom_ssl_context(self) -> None:
        custom_ctx = ssl.create_default_context()
        connector = create_secure_connector(ssl=custom_ctx)
        assert connector._ssl is custom_ctx

    @pytest.mark.asyncio
    async def test_accepts_connector_kwargs(self) -> None:
        connector = create_secure_connector(limit=50)
        assert connector.limit == 50
