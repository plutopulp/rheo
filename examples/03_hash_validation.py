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
from rheo.domain import DownloadStatus, FileConfig, HashConfig


async def main() -> None:
    """Download files with hash validation."""
    print("Starting hash validation example...")
    print("This demonstrates file integrity checking with SHA256\n")

    # In real-world usage, you typically:
    # 1. Download a checksums file (e.g., SHA256SUMS.txt)
    # 2. Parse it to extract hashes
    # 3. Download files with validation
    #
    # Example sources:
    # - Python releases: https://www.python.org/downloads/ → checksums
    # - Linux ISOs: https://ubuntu.com/download → SHA256SUMS
    # - GitHub releases: often include checksums.txt or SHA256SUMS
    # - PyPI packages: hashes in metadata
    #
    # For this demo, we've pre-calculated checksums for proof.ovh.net files:
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
        # File 1: Correct hash - will validate successfully ✓
        FileConfig(
            url="https://proof.ovh.net/files/1Mb.dat",
            description="1MB file with correct SHA256 (will succeed)",
            hash_config=HashConfig(
                algorithm="sha256",
                expected_hash=checksums["1Mb.dat"],
            ),
        ),
        # File 2: Intentionally wrong hash - will fail validation ✗
        # (Simulates corrupted file or tampered download)
        FileConfig(
            url="https://proof.ovh.net/files/10Mb.dat",
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
        print(f"  {i}. {f.description}")
        print(f"     Expected: {hash_display}")
    print()

    # Track results for summary
    successful = []
    failed = []

    # Process each file individually to show clear success/failure
    # Note: manager.tracker is automatically available for querying download status
    async with DownloadManager(download_dir=Path("./downloads")) as manager:
        for file_config in files:
            print(f"Downloading: {file_config.description}")

            await manager.add_to_queue([file_config])
            await manager.queue.join()

            # Check download status from manager's tracker
            info = manager.tracker.get_download_info(str(file_config.url))
            if info and info.status == DownloadStatus.FAILED:
                print(f"  ✗ Validation failed: {info.error}\n")
                failed.append((file_config.description, info.error or "Unknown error"))
            else:
                print("  ✓ Downloaded and validated successfully!\n")
                successful.append(file_config.description)

    # Summary
    print("=" * 70)
    print(f"Results: {len(successful)} validated, {len(failed)} failed")
    print("=" * 70)

    if successful:
        print("\n✓ Successfully validated:")
        for desc in successful:
            print(f"  - {desc}")

    if failed:
        print("\n✗ Failed validation:")
        for desc, error in failed:
            print(f"  - {desc}")
            # Show first line of error for brevity
            error_summary = error.split("\n")[0]
            print(f"    → {error_summary}")

    print("\n" + "=" * 70)
    print("Key takeaways:")
    print("=" * 70)
    print("• Hash validation catches corrupted, incomplete, or tampered files")
    print("• Always get checksums from trusted sources (project releases, etc.)")
    print("• Use SHA256 or SHA512 for security-sensitive files")
    print("• Handle HashMismatchError gracefully in production code")
    print("• This is how package managers (pip, npm, cargo) ensure integrity")


if __name__ == "__main__":
    asyncio.run(main())
