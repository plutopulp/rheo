#!/usr/bin/env python3
"""
03_hash_validation.py - File integrity verification with SHA256

Demonstrates:
- Real-world workflow: checksums → download → validate
- How software releases work (Linux ISOs, GitHub releases, Python packages)
- Handling both successful validation and hash mismatches
- Where hash values come from in practice

Note: Requires internet connection to run
"""
import asyncio
from pathlib import Path

from rheo import DownloadManager
from rheo.domain import DownloadStatus, FileConfig, FileExistsStrategy, HashConfig


async def main() -> None:
    """Download files with hash validation."""
    print("Starting hash validation example...")
    print("This demonstrates file integrity checking with SHA256\n")

    # For this demo, we use pre-calculated checksums for proof.ovh.net files:
    checksums = {
        "1Mb.dat": "788d1a44b1633c8594def083d1b650e4842ea3e38d88c90228e7d581c6425c68",
        "10Mb.dat": "fb3f168caf9db959b34817a3689b8476df1852a915813936c98dd51efbdbf7db",
    }

    print("Checksums manifest (simulates downloaded SHA256SUMS.txt):")
    for filename, checksum in checksums.items():
        print(f"  {checksum}  {filename}")
    print()

    # Create file configs using checksums from manifest
    files = [
        # File 1: Correct hash -> will validate successfully
        FileConfig(
            url="https://proof.ovh.net/files/1Mb.dat",
            filename="03-hash-valid-1Mb.dat",
            destination_subdir="example_03",
            description="1MB file with correct SHA256 (will succeed)",
            hash_config=HashConfig(
                algorithm="sha256",
                expected_hash=checksums["1Mb.dat"],
            ),
        ),
        # File 2: Intentionally wrong hash -> will fail validation
        FileConfig(
            url="https://proof.ovh.net/files/10Mb.dat",
            filename="03-hash-invalid-10Mb.dat",
            destination_subdir="example_03",
            description="10MB file with WRONG hash (will fail)",
            hash_config=HashConfig(
                algorithm="sha256",
                expected_hash="0" * 64,  # Obviously incorrect hash
            ),
        ),
    ]

    print("Files to download and validate:")
    for i, f in enumerate(files, 1):
        hash_display = f.hash_config.expected_hash[:16] + "..."
        print(f"\t{i}. {f.description}")
        print(f"\tExpected: {hash_display}")
    print()

    # Track results for summary
    successful = []
    failed = []

    # Process each file individually to show clear success/failure
    # Note: manager.tracker is automatically available for querying download status
    async with DownloadManager(
        download_dir=Path("./downloads"),
        file_exists_strategy=FileExistsStrategy.OVERWRITE,
    ) as manager:
        for file_config in files:
            print(f"Downloading: {file_config.description}")

            await manager.add([file_config])
            await manager.wait_until_complete()

            # Check download status from manager's tracker
            info = manager.tracker.get_download_info(str(file_config.id))
            if info and info.status == DownloadStatus.FAILED:
                print(f"\tValidation failed: {info.error}\n")
                failed.append((file_config.description, info.error or "Unknown error"))
            else:
                print("\tDownloaded and validated successfully\n")
                successful.append(file_config.description)

    # Summary
    print(f"Results: {len(successful)} validated, {len(failed)} failed")

    if successful:
        print("\nSuccessfully validated:")
        for desc in successful:
            print(f"\t- {desc}")

    if failed:
        print("\nFailed validation:")
        for desc, error in failed:
            print(f"\t- {desc}")
            # Show first line of error for brevity
            error_summary = error.split("\n")[0]
            print(f"\t{error_summary}")


if __name__ == "__main__":
    asyncio.run(main())
