from urllib.parse import urlparse


# TODO: Add sanitization for invalid characters and path traversal.
def generate_filename(url: str) -> str:
    """Generate filename from URL by combining domain and path.

    Returns format: "domain-filename" or just "domain" if no path.
    TODO: Add sanitization for invalid characters and path traversal.
    """
    parsed_url = urlparse(url)
    path_part = parsed_url.path.strip("/")

    if path_part:
        # Extract filename from path, remove query params
        path_part = path_part.split("/")[-1].split("?")[0]
        return f"{parsed_url.netloc}-{path_part}"
    else:
        # No path, use domain only
        return parsed_url.netloc
