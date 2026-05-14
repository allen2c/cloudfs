"""CloudFS entry point."""

from .backend.gcs import GCSPath
from .version import VERSION

__version__ = VERSION


def from_uri(uri: str):
    """Create a CloudPath from a URI (e.g. gs://bucket/key)."""
    if uri.startswith("gs://"):
        return GCSPath.from_uri(uri)
    raise ValueError(f"Unsupported URI scheme: {uri!r}")
