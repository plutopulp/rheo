"""Tests for NullEmitter implementation."""

from typing import Any

import pytest

from rheo.events import BaseEmitter, NullEmitter


@pytest.fixture
def null_emitter():
    """Provide a NullEmitter instance for testing."""
    return NullEmitter()


class TestNullEmitter:
    """Test NullEmitter implementation."""

    @pytest.mark.asyncio
    async def test_null_emitter_implements_base_emitter(self, null_emitter):
        """Test that NullEmitter inherits from BaseEmitter."""
        assert isinstance(null_emitter, BaseEmitter)

    @pytest.mark.asyncio
    async def test_all_methods_do_nothing_without_error(self, null_emitter):
        """Test that all emitter methods can be called without errors."""

        def handler(_: Any) -> None:
            pass

        # Should not raise any exceptions
        null_emitter.on("event", handler)
        await null_emitter.emit("event", {"data": "test"})
        null_emitter.off("event", handler)
