"""Google Cloud Storage backend for CloudFS."""

from __future__ import annotations

from typing import IO, Any, Generator, Iterator

from cloudfs.base import CloudPath


class GCSPath(CloudPath):
    """pathlib.Path-compatible interface for Google Cloud Storage."""

    def __init__(self, bucket: str, key: str = "", _client=None):
        self._bucket_name = bucket
        self._key = key.strip("/") if key else ""
        self.__client = _client

    @property
    def _client(self):
        if self.__client is None:
            from google.cloud import storage

            self.__client = storage.Client()
        return self.__client

    @property
    def _bucket(self):
        return self._client.bucket(self._bucket_name)

    @property
    def _blob(self):
        return self._bucket.blob(self._key)

    def _child(self, key: str) -> "GCSPath":
        return GCSPath(self._bucket_name, key, _client=self.__client)

    def __str__(self) -> str:
        if self._key:
            return f"gs://{self._bucket_name}/{self._key}"
        return f"gs://{self._bucket_name}"

    def __repr__(self) -> str:
        return f"GCSPath('{self}')"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GCSPath):
            return self._bucket_name == other._bucket_name and self._key == other._key
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._bucket_name, self._key))

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
        return f"gs://{self._bucket_name}"

    @property
    def root(self) -> str:
        return "/"

    @property
    def anchor(self) -> str:
        return f"gs://{self._bucket_name}/"

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
    def parent(self) -> "GCSPath":
        if "/" in self._key:
            return self._child("/".join(self._key.split("/")[:-1]))
        return self._child("")

    @property
    def parents(self) -> list["GCSPath"]:
        parts = self._key.split("/") if self._key else []
        result = []
        for i in range(len(parts) - 1, -1, -1):
            result.append(self._child("/".join(parts[:i])))
        return result

    @property
    def parts(self) -> tuple[str, ...]:
        root = f"gs://{self._bucket_name}/"
        if not self._key:
            return (root,)
        return (root,) + tuple(self._key.split("/"))

    def __truediv__(self, other: str) -> "GCSPath":
        other = str(other).strip("/")
        new_key = f"{self._key}/{other}" if self._key else other
        return self._child(new_key)

    def joinpath(self, *others: str) -> "GCSPath":
        result = self
        for part in others:
            result = result / part
        return result

    def with_name(self, name: str) -> "GCSPath":
        if not self._key:
            raise ValueError("CloudPath has no name component")
        parent_key = "/".join(self._key.split("/")[:-1])
        new_key = f"{parent_key}/{name}" if parent_key else name
        return self._child(new_key)

    def with_stem(self, stem: str) -> "GCSPath":
        return self.with_name(stem + self.suffix)

    def with_suffix(self, suffix: str) -> "GCSPath":
        if suffix and not suffix.startswith("."):
            raise ValueError(f"Invalid suffix: {suffix!r}")
        return self.with_name(self.stem + suffix)

    def is_absolute(self) -> bool:
        return True

    def resolve(self, strict: bool = False) -> "GCSPath":
        return self._child(self._key)

    def absolute(self) -> "GCSPath":
        return self._child(self._key)

    def exists(self) -> bool:
        if not self._key:
            return self._bucket.exists()
        if self._blob.exists():
            return True
        prefix = self._key.rstrip("/") + "/"
        blobs = self._client.list_blobs(self._bucket_name, prefix=prefix, max_results=1)
        return any(True for _ in blobs)

    def is_file(self) -> bool:
        return bool(self._key) and self._blob.exists()

    def samefile(self, other: "CloudPath") -> bool:
        if not isinstance(other, GCSPath):
            return False
        return self._bucket_name == other._bucket_name and self._key == other._key

    def is_dir(self) -> bool:
        if not self._key:
            return self._bucket.exists()
        if self._blob.exists():
            return False
        prefix = self._key.rstrip("/") + "/"
        blobs = self._client.list_blobs(self._bucket_name, prefix=prefix, max_results=1)
        return any(True for _ in blobs)

    def iterdir(self) -> Iterator["GCSPath"]:
        prefix = (self._key.rstrip("/") + "/") if self._key else ""
        seen: set[str] = set()
        blobs = self._client.list_blobs(self._bucket_name, prefix=prefix, delimiter="/")
        for blob in blobs:
            rel = blob.name[len(prefix) :]
            top = rel.split("/")[0]
            if top and top not in seen:
                seen.add(top)
                yield self._child(prefix + top)
        for prefix_item in blobs.prefixes:  # type: ignore[union-attr]
            rel = prefix_item[len(prefix) :].rstrip("/")
            if rel and rel not in seen:
                seen.add(rel)
                yield self._child(prefix + rel)

    def glob(self, pattern: str) -> Iterator["GCSPath"]:
        import fnmatch

        prefix = (self._key.rstrip("/") + "/") if self._key else ""
        for blob in self._client.list_blobs(self._bucket_name, prefix=prefix):
            rel = blob.name[len(prefix) :]
            if fnmatch.fnmatch(rel, pattern):
                yield self._child(blob.name)

    def walk(
        self,
        top_down: bool = True,
        on_error: Any = None,
    ) -> Generator[tuple["GCSPath", list[str], list[str]], None, None]:
        from collections import defaultdict

        prefix = (self._key.rstrip("/") + "/") if self._key else ""
        tree: dict[str, tuple[list[str], list[str]]] = defaultdict(lambda: ([], []))
        tree[self._key]  # ensure root exists

        try:
            for blob in self._client.list_blobs(self._bucket_name, prefix=prefix):
                rel = blob.name[len(prefix):]
                if not rel:
                    continue
                parts = rel.split("/")
                dir_key = self._key
                for i, part in enumerate(parts[:-1]):
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

        def _yield(key: str) -> Generator[tuple["GCSPath", list[str], list[str]], None, None]:
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

    def rglob(self, pattern: str) -> Iterator["GCSPath"]:
        import fnmatch

        prefix = (self._key.rstrip("/") + "/") if self._key else ""
        for blob in self._client.list_blobs(self._bucket_name, prefix=prefix):
            rel = blob.name[len(prefix) :]
            if fnmatch.fnmatch(rel, "**/" + pattern) or fnmatch.fnmatch(rel, pattern):
                yield self._child(blob.name)

    def open(
        self,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> IO:
        return self._blob.open(mode=mode, encoding=encoding, errors=errors, newline=newline)

    def read_bytes(self) -> bytes:
        return self._blob.download_as_bytes()

    def read_text(self, encoding: str = "utf-8") -> str:
        return self._blob.download_as_text(encoding=encoding)

    def write_bytes(self, data: bytes) -> int:
        self._blob.upload_from_string(data, content_type="application/octet-stream")
        return len(data)

    def write_text(self, data: str, encoding: str = "utf-8") -> int:
        encoded = data.encode(encoding)
        self._blob.upload_from_string(encoded, content_type="text/plain")
        return len(encoded)

    def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
        if self._blob.exists():
            if not exist_ok:
                raise FileExistsError(str(self))
            return
        self._blob.upload_from_string(b"")

    def unlink(self, missing_ok: bool = False) -> None:
        if not self._blob.exists():
            if missing_ok:
                return
            raise FileNotFoundError(str(self))
        self._blob.delete()

    def rename(self, target: "GCSPath | str") -> "GCSPath":
        if isinstance(target, str):
            target = GCSPath.from_uri(target)
        self._bucket.copy_blob(self._blob, target._bucket, target._key)
        self._blob.delete()
        return target

    def replace(self, target: "GCSPath | str") -> "GCSPath":
        return self.rename(target)

    def rmdir(self) -> None:
        placeholder = self._key.rstrip("/") + "/"
        blob = self._bucket.blob(placeholder)
        if not blob.exists():
            raise FileNotFoundError(str(self))
        prefix = placeholder
        blobs = self._client.list_blobs(self._bucket_name, prefix=prefix, max_results=2)
        children = [b for b in blobs if b.name != placeholder]
        if children:
            raise OSError(f"Directory not empty: {self}")
        blob.delete()

    def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None:
        if self.exists():
            if exist_ok:
                return
            raise FileExistsError(str(self))
        placeholder = self._key.rstrip("/") + "/"
        self._bucket.blob(placeholder).upload_from_string(b"")

    def stat(self) -> "GCSStatResult":
        blob = self._blob
        blob.reload()
        return GCSStatResult(blob)

    @classmethod
    def from_uri(cls, uri: str, _client=None) -> "GCSPath":
        if not uri.startswith("gs://"):
            raise ValueError(f"Not a GCS URI: {uri!r}")
        without_scheme = uri[5:]
        parts = without_scheme.split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return cls(bucket, key, _client=_client)


class GCSStatResult:
    def __init__(self, blob):
        self._blob = blob

    @property
    def st_size(self) -> int:
        return self._blob.size or 0

    @property
    def st_mtime(self) -> float:
        updated = self._blob.updated
        return updated.timestamp() if updated else 0.0

    @property
    def st_ctime(self) -> float:
        created = self._blob.time_created
        return created.timestamp() if created else 0.0

    def __repr__(self) -> str:
        return (
            f"GCSStatResult(st_size={self.st_size}, "
            f"st_mtime={self.st_mtime}, st_ctime={self.st_ctime})"
        )
