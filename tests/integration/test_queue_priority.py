"""Integration tests for queue priority ordering."""

import pytest
from aioresponses import CallbackResult, aioresponses

from rheo import DownloadManager
from rheo.domain import FileConfig


class TestBatchAddPriorityOrdering:
    """Tests that batch add respects priority ordering."""

    @pytest.mark.asyncio
    async def test_batch_add_processes_high_priority_first(
        self, tmp_path, aio_client, mock_logger
    ) -> None:
        """High priority item added second in batch should start first."""
        started_order: list[str] = []
        file_configs = {
            "low": FileConfig(
                url="http://example.com/low.txt", filename="low.txt", priority=1
            ),
            "high": FileConfig(
                url="http://example.com/high.txt", filename="high.txt", priority=10
            ),
        }

        def make_callback(file_config: FileConfig, body: bytes = b"content"):
            def _cb(url, **kwargs):
                started_order.append(file_config.id)
                return CallbackResult(status=200, body=body)

            return _cb

        with aioresponses() as mock:
            # Both responses are fast; ordering comes from queue behaviour
            mock.get(
                str(file_configs["low"].url),
                callback=make_callback(file_configs["low"]),
                repeat=True,
            )
            mock.get(
                str(file_configs["high"].url),
                callback=make_callback(file_configs["high"]),
                repeat=True,
            )

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                max_concurrent=1,
                logger=mock_logger,
            ) as manager:

                # Add low priority FIRST, high priority SECOND.
                # High priority should still start first once the batch is queued.
                await manager.add(list(file_configs.values()))
                await manager.wait_until_complete()

        # High priority should have started first despite being added second
        assert len(started_order) == 2
        assert started_order == [file_configs["high"].id, file_configs["low"].id]
