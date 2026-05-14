from typing import Protocol
from .version import VERSION


__version__ = VERSION


def from_uri(uri: str) -> "CloudPath": ...


class CloudPath(Protocol): ...
