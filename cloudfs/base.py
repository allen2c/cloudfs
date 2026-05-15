"""CloudPath abstract base — the public Path interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import IO, Any, Generator, Iterator

from .exceptions import CloudOperationError


class CloudPath(ABC):
    """Abstract base for all cloud paths. Dispatches to backend on construction.

    Usage:
        from cloudfs import Path
        p = Path("gs://bucket/key")
    """

    def __new__(cls, *args, **kwargs) -> "CloudPath":
        if cls is CloudPath:
            uri = args[0] if args else ""
            if uri.startswith("gs://"):
                from .backend.gcs import GCSPath

                return GCSPath.from_uri(uri)
            raise ValueError(f"Unsupported URI scheme: {uri!r}")
        return object.__new__(cls)

    @abstractmethod
    def __str__(self) -> str: ...

    @abstractmethod
    def __repr__(self) -> str: ...

    @abstractmethod
    def __eq__(self, other: object) -> bool: ...

    @abstractmethod
    def __hash__(self) -> int: ...

    @abstractmethod
    def __truediv__(self, other: str) -> "CloudPath": ...

    @abstractmethod
    def __lt__(self, other: "CloudPath") -> bool: ...

    @abstractmethod
    def __le__(self, other: "CloudPath") -> bool: ...

    @abstractmethod
    def __gt__(self, other: "CloudPath") -> bool: ...

    @abstractmethod
    def __ge__(self, other: "CloudPath") -> bool: ...

    @property
    @abstractmethod
    def drive(self) -> str: ...

    @property
    @abstractmethod
    def root(self) -> str: ...

    @property
    @abstractmethod
    def anchor(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def stem(self) -> str: ...

    @property
    @abstractmethod
    def suffix(self) -> str: ...

    @property
    @abstractmethod
    def suffixes(self) -> list[str]: ...

    @property
    @abstractmethod
    def parent(self) -> "CloudPath": ...

    @property
    @abstractmethod
    def parents(self) -> list["CloudPath"]: ...

    @property
    @abstractmethod
    def parts(self) -> tuple[str, ...]: ...

    @abstractmethod
    def joinpath(self, *others: str) -> "CloudPath": ...

    @abstractmethod
    def with_name(self, name: str) -> "CloudPath": ...

    @abstractmethod
    def with_stem(self, stem: str) -> "CloudPath": ...

    @abstractmethod
    def with_suffix(self, suffix: str) -> "CloudPath": ...

    @abstractmethod
    def is_absolute(self) -> bool: ...

    @abstractmethod
    def resolve(self, strict: bool = False) -> "CloudPath": ...

    @abstractmethod
    def absolute(self) -> "CloudPath": ...

    @abstractmethod
    def exists(self) -> bool: ...

    @abstractmethod
    def is_file(self) -> bool: ...

    @abstractmethod
    def is_dir(self) -> bool: ...

    @abstractmethod
    def samefile(self, other: "CloudPath") -> bool: ...

    @abstractmethod
    def iterdir(self) -> Iterator["CloudPath"]: ...

    @abstractmethod
    def walk(
        self,
        top_down: bool = True,
        on_error: Any = None,
    ) -> Generator[tuple["CloudPath", list[str], list[str]], None, None]: ...

    @abstractmethod
    def glob(self, pattern: str) -> Iterator["CloudPath"]: ...

    @abstractmethod
    def rglob(self, pattern: str) -> Iterator["CloudPath"]: ...

    @abstractmethod
    def open(
        self,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> IO: ...

    @abstractmethod
    def read_bytes(self) -> bytes: ...

    @abstractmethod
    def read_text(self, encoding: str = "utf-8") -> str: ...

    @abstractmethod
    def write_bytes(self, data: bytes) -> int: ...

    @abstractmethod
    def write_text(self, data: str, encoding: str = "utf-8") -> int: ...

    @abstractmethod
    def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None: ...

    @abstractmethod
    def unlink(self, missing_ok: bool = False) -> None: ...

    @abstractmethod
    def rename(self, target: "CloudPath | str") -> "CloudPath": ...

    @abstractmethod
    def replace(self, target: "CloudPath | str") -> "CloudPath": ...

    @abstractmethod
    def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None: ...

    @abstractmethod
    def rmdir(self) -> None: ...

    @abstractmethod
    def stat(self, follow_symlinks: bool = True) -> Any: ...

    def relative_to(self, *other: "CloudPath | str") -> "CloudPath":
        raise CloudOperationError(
            "relative_to() is not supported: cloud paths are always absolute."
        )

    def is_relative_to(self, *other: "CloudPath | str") -> bool:
        raise CloudOperationError(
            "is_relative_to() is not supported: cloud paths are always absolute."
        )

    def is_symlink(self) -> bool:
        raise CloudOperationError("Cloud storage does not support symlinks.")

    def is_mount(self) -> bool:
        raise CloudOperationError("Cloud storage does not support mount points.")

    def is_junction(self) -> bool:
        raise CloudOperationError("Cloud storage does not support junctions.")

    def is_block_device(self) -> bool:
        raise CloudOperationError("Cloud storage does not have block devices.")

    def is_char_device(self) -> bool:
        raise CloudOperationError("Cloud storage does not have char devices.")

    def is_fifo(self) -> bool:
        raise CloudOperationError("Cloud storage does not support FIFOs.")

    def is_socket(self) -> bool:
        raise CloudOperationError("Cloud storage does not support sockets.")

    def lstat(self) -> Any:
        raise CloudOperationError(
            "lstat() is not supported: cloud storage has no symlinks."
        )

    def chmod(self, mode: int, follow_symlinks: bool = True) -> None:
        raise CloudOperationError(
            "chmod() is not supported: cloud storage has no POSIX permissions."
        )

    def lchmod(self, mode: int) -> None:
        raise CloudOperationError(
            "lchmod() is not supported: cloud storage has no POSIX permissions."
        )

    def symlink_to(self, target: Any, target_is_directory: bool = False) -> None:
        raise CloudOperationError("Cloud storage does not support symlinks.")

    def hardlink_to(self, target: Any) -> None:
        raise CloudOperationError("Cloud storage does not support hard links.")

    def expanduser(self) -> "CloudPath":
        raise CloudOperationError(
            "expanduser() is not supported: cloud paths have no home directory."
        )

    @classmethod
    def home(cls) -> "CloudPath":
        raise CloudOperationError(
            "home() is not supported: cloud paths have no home directory."
        )

    @classmethod
    def cwd(cls) -> "CloudPath":
        raise CloudOperationError(
            "cwd() is not supported: cloud paths have no working directory."
        )
