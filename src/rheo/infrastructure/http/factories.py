"""Factory functions for HTTP client components."""

import ssl
import typing as t

import aiohttp
import certifi


def create_ssl_context() -> ssl.SSLContext:
    """Create SSL context with certifi's certificate bundle.

    Uses certifi to ensure proper HTTPS verification on all platforms, including
    environments where system certificates may not be loaded by default.
    """
    return ssl.create_default_context(cafile=certifi.where())


def create_secure_connector(**connector_kwargs: t.Any) -> aiohttp.TCPConnector:
    """Create TCP connector with secure SSL defaults.

    Args:
        **connector_kwargs: Passed to TCPConnector (e.g., limit, ttl_dns_cache).
                           If 'ssl' is provided, it overrides the default context.
    """
    ssl_ctx = connector_kwargs.pop("ssl", None) or create_ssl_context()
    return aiohttp.TCPConnector(ssl=ssl_ctx, **connector_kwargs)
