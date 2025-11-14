"""Test files of various sizes and types for testing download manager
with real URLs.
Categories: small (<1MB), medium (1-10MB), large (10-100MB), xl (>100MB)
Special cases: slow_drip, chunked_data, delayed_response, likely_to_fail

"""

from pydantic import HttpUrl

from async_download_manager.domain.file_config import FileConfig

TEST_FILES: dict[str, FileConfig] = {
    # Small files (< 1MB) - Quick downloads for basic testing
    "small_text": FileConfig(
        url=HttpUrl("https://raw.githubusercontent.com/nodejs/node/master/README.md"),
        size_bytes=10_000,
        size_human="10 KB",
        type="text/markdown",
        description="Node.js README file",
        priority=1,
    ),
    "small_json": FileConfig(
        url=HttpUrl("https://jsonplaceholder.typicode.com/users"),
        size_bytes=5_000,
        size_human="5 KB",
        type="application/json",
        description="Sample user data in JSON format",
        priority=1,
    ),
    "small_image": FileConfig(
        url=HttpUrl("https://picsum.photos/200/300"),
        size_bytes=15_000,
        size_human="15 KB",
        type="image/jpeg",
        description="Random small image",
        priority=1,
    ),
    # Medium files (1MB - 10MB)
    "medium_binary": FileConfig(
        url=HttpUrl("https://proof.ovh.net/files/1Mb.dat"),
        size_bytes=1_048_576,
        size_human="1 MB",
        type="application/octet-stream",
        description="1MB binary test file",
        priority=2,
    ),
    "medium_image": FileConfig(
        url=HttpUrl(
            "https://file-examples.com/wp-content/storage/2017/10/"
            + "file_example_PNG_1MB.png"
        ),
        size_bytes=1_000_000,
        size_human="1 MB",
        type="image/png",
        description="Sample 1MB PNG image",
        priority=2,
    ),
    "medium_audio": FileConfig(
        url=HttpUrl(
            "https://file-examples.com/wp-content/uploads/2017/11/"
            + "file_example_MP3_5MG.mp3"
        ),
        size_bytes=5_000_000,
        size_human="5 MB",
        type="audio/mp3",
        description="Sample 5MB MP3 audio file",
        priority=3,
    ),
    "medium_zip": FileConfig(
        url=HttpUrl("http://ipv4.download.thinkbroadband.com/5MB.zip"),
        size_bytes=5_000_000,
        size_human="5 MB",
        type="application/zip",
        description="5MB zip test file",
        priority=3,
    ),
    "medium_pdf": FileConfig(
        url=HttpUrl("https://research.nhm.org/pdfs/10840/10840.pdf"),
        size_bytes=3_000_000,
        size_human="3 MB",
        type="application/pdf",
        description="Sample research PDF",
        priority=3,
    ),
    # Large files (10MB - 100MB)
    "large_binary": FileConfig(
        url=HttpUrl("https://proof.ovh.net/files/10Mb.dat"),
        size_bytes=10_485_760,
        size_human="10 MB",
        type="application/octet-stream",
        description="10MB binary test file",
        priority=4,
    ),
    "large_video": FileConfig(
        url=HttpUrl(
            "https://file-examples.com/wp-content/uploads/2017/04/"
            "file_example_MP4_1920_18MG.mp4"
        ),
        size_bytes=18_000_000,
        size_human="18 MB",
        type="video/mp4",
        description="Sample 18MB MP4 video file",
        priority=4,
    ),
    "large_zip": FileConfig(
        url=HttpUrl("http://ipv4.download.thinkbroadband.com/20MB.zip"),
        size_bytes=20_000_000,
        size_human="20 MB",
        type="application/zip",
        description="20MB zip test file",
        priority=4,
    ),
    # Very large files (>100MB) - use with caution
    "xl_binary": FileConfig(
        url=HttpUrl("https://speed.hetzner.de/100MB.bin"),
        size_bytes=100_000_000,
        size_human="100 MB",
        type="application/octet-stream",
        description="100MB binary test file",
        priority=5,
    ),
    "xl_dat": FileConfig(
        url=HttpUrl("https://proof.ovh.net/files/100Mb.dat"),
        size_bytes=100_000_000,
        size_human="100 MB",
        type="application/octet-stream",
        description="100MB data test file",
        priority=5,
    ),
    # Special test cases
    "slow_drip": FileConfig(
        url=HttpUrl("https://httpbin.org/drip?duration=10&numbytes=1000&code=200"),
        size_bytes=1_000,
        size_human="1 KB",
        type="application/octet-stream",
        description="Slowly drips data over 10 seconds (good for testing progress)",
        priority=2,
    ),
    "chunked_data": FileConfig(
        url=HttpUrl("https://httpbin.org/stream-bytes/1048576?chunk_size=65536"),
        size_bytes=1_048_576,
        size_human="1 MB",
        type="application/octet-stream",
        description="Streams 1MB in 64KB chunks",
        priority=2,
    ),
    "delayed_response": FileConfig(
        url=HttpUrl("https://httpbin.org/delay/3"),
        size_bytes=500,
        size_human="500 B",
        type="application/json",
        description="Returns a response after 3 seconds (good for testing timeouts)",
        priority=1,
    ),
    "random_bytes": FileConfig(
        url=HttpUrl("https://httpbin.org/bytes/512000"),
        size_bytes=512_000,
        size_human="500 KB",
        type="application/octet-stream",
        description="500KB of random bytes",
        priority=1,
    ),
    "likely_to_fail": FileConfig(
        url=HttpUrl("https://thisdomainprobablydoesntexist.org/file.txt"),
        size_bytes=None,
        size_human="Unknown",
        type="text/plain",
        description="Non-existent domain (for testing error handling)",
        priority=1,
    ),
}


def get_file_config(name: str) -> FileConfig:
    """Get test file config by name. Raises KeyError if not found."""
    return TEST_FILES[name]


if __name__ == "__main__":
    # print(TEST_FILES.keys())
    print(get_file_config("large_video"))
