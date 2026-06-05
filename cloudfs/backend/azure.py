"""Azure Blob Storage backend for CloudFS.

Azure-specific behavior and known differences from local filesystems:

Directories:
    Azure Blob Storage has no real directories — only blob names containing
    slashes. Directories are simulated either by placeholder blobs (a zero-byte
    blob named "prefix/") created by mkdir(), or implicitly by blobs that share
    a common prefix.

    - mkdir() creates a placeholder blob. If all files under a directory are
      unlinked but the placeholder remains, is_dir() still returns True.
    - Writing directly to a sub-path (write_text, write_bytes) never requires
      a prior mkdir(), unlike local filesystems.
    - A path can simultaneously satisfy is_file() and is_dir() if a blob named
      "foo" and another named "foo/bar" both exist. This cannot happen locally.

rmdir():
    Only removes the placeholder blob created by mkdir(). A "virtual" directory
    that was never explicitly created will raise FileNotFoundError even if
    is_dir() returns True.

open():
    Read modes stream the blob via a chunked reader; write modes stream the
    upload by staging blocks and committing them on close. Memory use is bounded
    by the upload chunk size, not the blob size. read_bytes/write_bytes still
    load the whole blob, matching pathlib semantics.

rename():
    Implemented as copy + delete. Not atomic — a crash between the two steps
    leaves both source and destination in place.

Consistency:
    Azure Blob Storage provides strong consistency for all operations.

Performance:
    Each exists(), is_file(), and is_dir() call makes at least one API request.
    Avoid calling them in tight loops; prefer bulk listing via iterdir() or walk().
"""

from __future__ import annotations

import base64
import io
from typing import IO, Any, Generator, Iterator

from cloudfs.base import CloudPath

# Streaming upload block size. Bounds the memory held during a streaming
# open("wb"); a chunk is staged as a block and the block list committed on close.
_UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024


class AzurePath(CloudPath):
    """pathlib.Path-compatible interface for Azure Blob Storage.

    URI format: az://container/blob
    Credentials: set AZURE_STORAGE_CONNECTION_STRING in environment.
    """

    def __init__(self, container: str, key: str = "", _client=None):
        self._container_name = container
        self._key = key.strip("/") if key else ""
        self.__client = _client

    @property
    def _client(self):
        if self.__client is None:
            import os

            from azure.storage.blob import BlobServiceClient

            conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
            self.__client = BlobServiceClient.from_connection_string(conn_str)
        return self.__client

    @property
    def _container(self):
        return self._client.get_container_client(self._container_name)

    def _child(self, key: str) -> "AzurePath":
        return AzurePath(self._container_name, key, _client=self.__client)

    def __str__(self) -> str:
        if self._key:
            return f"az://{self._container_name}/{self._key}"
        return f"az://{self._container_name}"

    def __repr__(self) -> str:
        return f"AzurePath('{self}')"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AzurePath):
            return (
                self._container_name == other._container_name
                and self._key == other._key
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._container_name, self._key))

    def __lt__(self, other: "CloudPath") -> bool:
        return str(self) < str(other)

    def __le__(self, other: "CloudPath") -> bool:
        return str(self) <= str(other)

    def __gt__(self, other: "CloudPath") -> bool:
        return str(self) > str(other)

    def __ge__(self, other: "CloudPath") -> bool:
        return str(self) >= str(other)

    @property
    def drive(self) -> str:
        return f"az://{self._container_name}"

    @property
    def root(self) -> str:
        return "/"

    @property
    def anchor(self) -> str:
        return f"az://{self._container_name}/"

    @property
    def name(self) -> str:
        return self._key.split("/")[-1] if self._key else ""

    @property
    def stem(self) -> str:
        n = self.name
        idx = n.rfind(".")
        return n[:idx] if idx > 0 else n

    @property
    def suffix(self) -> str:
        n = self.name
        idx = n.rfind(".")
        return n[idx:] if idx > 0 else ""

    @property
    def suffixes(self) -> list[str]:
        parts = self.name.split(".")
        return ["." + p for p in parts[1:]] if len(parts) > 1 else []

    @property
    def parent(self) -> "AzurePath":
        if "/" in self._key:
            return self._child("/".join(self._key.split("/")[:-1]))
        return self._child("")

    @property
    def parents(self) -> list["AzurePath"]:
        parts = self._key.split("/") if self._key else []
        result = []
        for i in range(len(parts) - 1, -1, -1):
            result.append(self._child("/".join(parts[:i])))
        return result

    @property
    def parts(self) -> tuple[str, ...]:
        root = f"az://{self._container_name}/"
        if not self._key:
            return (root,)
        return (root,) + tuple(self._key.split("/"))

    def __truediv__(self, other: str) -> "AzurePath":
        other = str(other).strip("/")
        new_key = f"{self._key}/{other}" if self._key else other
        return self._child(new_key)

    def joinpath(self, *others: str) -> "AzurePath":
        result = self
        for part in others:
            result = result / part
        return result

    def with_name(self, name: str) -> "AzurePath":
        if not self._key:
            raise ValueError("AzurePath has no name component")
        parent_key = "/".join(self._key.split("/")[:-1])
        new_key = f"{parent_key}/{name}" if parent_key else name
        return self._child(new_key)

    def with_stem(self, stem: str) -> "AzurePath":
        return self.with_name(stem + self.suffix)

    def with_suffix(self, suffix: str) -> "AzurePath":
        if suffix and not suffix.startswith("."):
            raise ValueError(f"Invalid suffix: {suffix!r}")
        return self.with_name(self.stem + suffix)

    def is_absolute(self) -> bool:
        return True

    def resolve(self, strict: bool = False) -> "AzurePath":
        return self._child(self._key)

    def absolute(self) -> "AzurePath":
        return self._child(self._key)

    def _blob_exists(self) -> bool:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            self._container.get_blob_client(self._key).get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False

    def _has_children(self, prefix: str) -> bool:
        items = self._container.list_blobs(name_starts_with=prefix)
        return any(True for _ in items)

    def exists(self) -> bool:
        if not self._key:
            try:
                self._container.get_container_properties()
                return True
            except Exception:
                return False
        if self._blob_exists():
            return True
        return self._has_children(self._key.rstrip("/") + "/")

    def is_file(self) -> bool:
        return bool(self._key) and self._blob_exists()

    def is_dir(self) -> bool:
        if not self._key:
            return self.exists()
        if self._blob_exists():
            return False
        return self._has_children(self._key.rstrip("/") + "/")

    def samefile(self, other: "CloudPath") -> bool:
        if not isinstance(other, AzurePath):
            return False
        return self._container_name == other._container_name and self._key == other._key

    def iterdir(self) -> Iterator["AzurePath"]:
        from azure.storage.blob import BlobPrefix

        prefix = (self._key.rstrip("/") + "/") if self._key else ""
        seen: set[str] = set()
        for item in self._container.walk_blobs(name_starts_with=prefix, delimiter="/"):
            if isinstance(item, BlobPrefix):
                rel = item.name[len(prefix) :].rstrip("/")
            else:
                rel = item.name[len(prefix) :]
                rel = rel.split("/")[0]
            if rel and rel not in seen:
                seen.add(rel)
                yield self._child(prefix + rel)

    def glob(self, pattern: str) -> Iterator["AzurePath"]:
        import fnmatch

        prefix = (self._key.rstrip("/") + "/") if self._key else ""
        for blob in self._container.list_blobs(name_starts_with=prefix):
            rel = blob.name[len(prefix) :]
            if fnmatch.fnmatch(rel, pattern):
                yield self._child(blob.name)

    def rglob(self, pattern: str) -> Iterator["AzurePath"]:
        import fnmatch

        prefix = (self._key.rstrip("/") + "/") if self._key else ""
        for blob in self._container.list_blobs(name_starts_with=prefix):
            rel = blob.name[len(prefix) :]
            if fnmatch.fnmatch(rel, "**/" + pattern) or fnmatch.fnmatch(rel, pattern):
                yield self._child(blob.name)

    def walk(
        self,
        top_down: bool = True,
        on_error: Any = None,
    ) -> Generator[tuple["AzurePath", list[str], list[str]], None, None]:
        from collections import defaultdict

        prefix = (self._key.rstrip("/") + "/") if self._key else ""
        tree: dict[str, tuple[list[str], list[str]]] = defaultdict(lambda: ([], []))
        tree[self._key]

        try:
            for blob in self._container.list_blobs(name_starts_with=prefix):
                rel = blob.name[len(prefix) :]
                if not rel:
                    continue
                parts = rel.split("/")
                dir_key = self._key
                for part in parts[:-1]:
                    parent_key = dir_key
                    dir_key = f"{dir_key}/{part}" if dir_key else part
                    if part not in tree[parent_key][0]:
                        tree[parent_key][0].append(part)
                    tree[dir_key]
                tree[dir_key][1].append(parts[-1])
        except Exception as e:
            if on_error:
                on_error(e)
            return

        def _yield(
            key: str,
        ) -> Generator[tuple["AzurePath", list[str], list[str]], None, None]:
            dirnames, filenames = tree[key]
            dirpath = self._child(key)
            if top_down:
                yield dirpath, list(dirnames), list(filenames)
                for d in dirnames:
                    child_key = f"{key}/{d}" if key else d
                    yield from _yield(child_key)
            else:
                for d in dirnames:
                    child_key = f"{key}/{d}" if key else d
                    yield from _yield(child_key)
                yield dirpath, list(dirnames), list(filenames)

        yield from _yield(self._key)

    def open(
        self,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> IO:
        if mode in ("rb", "r"):
            downloader = self._container.download_blob(self._key)
            buf = io.BufferedReader(_AzureReadBuffer(downloader))
            if mode == "r":
                return io.TextIOWrapper(
                    buf, encoding=encoding or "utf-8", errors=errors, newline=newline
                )
            return buf
        if mode in ("wb", "w"):
            raw = _AzureWriteBuffer(self._container, self._key)
            if mode == "w":
                return io.TextIOWrapper(
                    io.BufferedWriter(raw),
                    encoding=encoding or "utf-8",
                    errors=errors,
                    newline=newline,
                )
            return raw
        raise ValueError(f"Unsupported mode: {mode!r}")

    def read_bytes(self) -> bytes:
        return self._container.download_blob(self._key).readall()

    def read_text(self, encoding: str = "utf-8") -> str:
        return self.read_bytes().decode(encoding)

    def write_bytes(self, data: bytes) -> int:
        self._container.upload_blob(self._key, data, overwrite=True)
        return len(data)

    def write_text(self, data: str, encoding: str = "utf-8") -> int:
        return self.write_bytes(data.encode(encoding))

    def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
        if self._blob_exists():
            if not exist_ok:
                raise FileExistsError(str(self))
            return
        self._container.upload_blob(self._key, b"", overwrite=True)

    def unlink(self, missing_ok: bool = False) -> None:
        if not self._blob_exists():
            if missing_ok:
                return
            raise FileNotFoundError(str(self))
        self._container.delete_blob(self._key)

    def rename(self, target: "AzurePath | str") -> "AzurePath":
        if isinstance(target, str):
            target = AzurePath.from_uri(target)
        src_url = self._container.get_blob_client(self._key).url
        dst_blob = target._container.get_blob_client(target._key)
        dst_blob.start_copy_from_url(src_url)
        self._container.delete_blob(self._key)
        return target

    def replace(self, target: "AzurePath | str") -> "AzurePath":
        return self.rename(target)

    def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None:
        if self.exists():
            if exist_ok:
                return
            raise FileExistsError(str(self))
        placeholder = self._key.rstrip("/") + "/"
        self._container.upload_blob(placeholder, b"", overwrite=True)

    def rmdir(self) -> None:
        from azure.core.exceptions import ResourceNotFoundError

        placeholder = self._key.rstrip("/") + "/"
        blob_client = self._container.get_blob_client(placeholder)
        try:
            blob_client.get_blob_properties()
        except ResourceNotFoundError:
            raise FileNotFoundError(str(self))
        children = [
            b
            for b in self._container.list_blobs(name_starts_with=placeholder)
            if b.name != placeholder
        ]
        if children:
            raise OSError(f"Directory not empty: {self}")
        self._container.delete_blob(placeholder)

    def stat(self, follow_symlinks: bool = True) -> "AzureStatResult":
        props = self._container.get_blob_client(self._key).get_blob_properties()
        return AzureStatResult(props)

    @classmethod
    def from_uri(cls, uri: str, _client=None) -> "AzurePath":
        if not uri.startswith("az://"):
            raise ValueError(f"Not an Azure URI: {uri!r}")
        without_scheme = uri[5:]
        parts = without_scheme.split("/", 1)
        container = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return cls(container, key, _client=_client)


class _AzureReadBuffer(io.RawIOBase):
    def __init__(self, downloader):
        self._chunks = downloader.chunks()
        self._leftover = b""

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:
        if not self._leftover:
            try:
                self._leftover = next(self._chunks)
            except StopIteration:
                return 0
        n = min(len(b), len(self._leftover))
        b[:n] = self._leftover[:n]
        self._leftover = self._leftover[n:]
        return n


class _AzureWriteBuffer(io.RawIOBase):
    def __init__(self, container, key):
        self._blob = container.get_blob_client(key)
        self._buf = bytearray()
        self._block_ids: list[str] = []

    def writable(self) -> bool:
        return True

    def write(self, data) -> int:
        self._buf.extend(data)
        while len(self._buf) >= _UPLOAD_CHUNK_SIZE:
            self._flush_block(_UPLOAD_CHUNK_SIZE)
        return len(data)

    def _flush_block(self, size: int) -> None:
        chunk = bytes(self._buf[:size])
        del self._buf[:size]
        block_id = base64.b64encode(f"{len(self._block_ids):032d}".encode()).decode()
        self._blob.stage_block(block_id, chunk)
        self._block_ids.append(block_id)

    def close(self) -> None:
        if self.closed:
            return
        from azure.storage.blob import BlobBlock

        try:
            if self._buf:
                self._flush_block(len(self._buf))
            block_list = [BlobBlock(block_id=bid) for bid in self._block_ids]
            self._blob.commit_block_list(block_list)
        finally:
            super().close()


class AzureStatResult:
    def __init__(self, props):
        self._props = props

    @property
    def st_size(self) -> int:
        return self._props.get("size", 0) or 0

    @property
    def st_mtime(self) -> float:
        dt = self._props.get("last_modified")
        return dt.timestamp() if dt else 0.0

    @property
    def st_ctime(self) -> float:
        dt = self._props.get("creation_time")
        return dt.timestamp() if dt else self.st_mtime

    def __repr__(self) -> str:
        return (
            f"AzureStatResult(st_size={self.st_size}, "
            f"st_mtime={self.st_mtime}, st_ctime={self.st_ctime})"
        )
