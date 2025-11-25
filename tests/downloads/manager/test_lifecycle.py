"""Tests for DownloadManager lifecycle and integration scenarios."""

import pytest


class TestDownloadLifecycle:
    """Test complete download lifecycle scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_add_wait_cycles_work(
        self,
        make_manager,
        make_file_configs,
        counting_download_mock,
    ):
        """Test that manager handles multiple add -> wait_until_complete cycles.

        Verifies that workers remain active after wait_until_complete() returns,
        allowing users to add more files and wait again without restarting.
        """
        download_mock = counting_download_mock(download_time=0.01)

        async with make_manager(
            max_concurrent=2, download_side_effect=download_mock
        ) as manager:
            # First batch
            batch1 = make_file_configs(count=2)
            await manager.add(batch1)
            await manager.wait_until_complete()
            assert download_mock.count["value"] == 2

            # Second batch - workers should still be running
            batch2 = make_file_configs(count=3)
            await manager.add(batch2)
            await manager.wait_until_complete()
            assert download_mock.count["value"] == 5

            # Third batch - still works!
            batch3 = make_file_configs(count=1)
            await manager.add(batch3)
            await manager.wait_until_complete()
            assert download_mock.count["value"] == 6

    @pytest.mark.asyncio
    async def test_manual_lifecycle_without_context_manager(
        self,
        make_manager,
        make_file_configs,
        counting_download_mock,
    ):
        """Test using manager with manual open/close instead of context manager."""
        download_mock = counting_download_mock(download_time=0.01)
        manager = make_manager(max_concurrent=2, download_side_effect=download_mock)

        # Use manual lifecycle
        await manager.open()

        try:
            # Add and wait for downloads
            batch1 = make_file_configs(count=2)
            await manager.add(batch1)
            await manager.wait_until_complete()
            assert download_mock.count["value"] == 2

            # Can add more
            batch2 = make_file_configs(count=1)
            await manager.add(batch2)
            await manager.wait_until_complete()
            assert download_mock.count["value"] == 3
        finally:
            await manager.close()
