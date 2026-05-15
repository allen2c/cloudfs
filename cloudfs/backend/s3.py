"""AWS S3 backend for CloudFS.

S3-specific behavior and known differences from local filesystems:

Directories:
    S3 has no real directories — only object keys containing slashes. Directories
    are simulated either by placeholder objects (a zero-byte object named "prefix/")
    created by mkdir(), or implicitly by objects that share a common prefix.

    - mkdir() creates a placeholder object. If all files under a directory are
      unlinked but the placeholder remains, is_dir() still returns True.
    - Writing directly to a sub-path (write_text, write_bytes) never requires
      a prior mkdir(), unlike local filesystems.
    - A path can simultaneously satisfy is_file() and is_dir() if an object named
      "foo" and another named "foo/bar" both exist. This cannot happen locally.

rmdir():
    Only removes the placeholder object created by mkdir(). A "virtual" directory
    that was never explicitly created will raise FileNotFoundError even if
    is_dir() returns True.

open():
    S3 has no native streaming file object. Read modes download the full object
    into memory. Write modes buffer in memory and upload on close.

Consistency:
    S3 provides strong read-after-write consistency for all operations since
    December 2020. No eventual-consistency caveats apply.

Performance:
    Each exists(), is_file(), and is_dir() call makes at least one API request.
    Avoid calling them in tight loops; prefer bulk listing via iterdir() or walk().
"""

from __future__ import annotations

import io
from typing import IO, Any, Generator, Iterator

from cloudfs.base import CloudPath


class S3Path(CloudPath):
    """pathlib.Path-compatible interface for AWS S3."""

    def __init__(self, bucket: str, key: str = "", _client=None):
        self._bucket_name = bucket
        self._key = key.strip("/") if key else ""
        self.__client = _client

    @property
    def _client(self):
        if self.__client is None:
            import boto3

            self.__client = boto3.client("s3")
        return self.__client

    def _child(self, key: str) -> "S3Path":
        return S3Path(self._bucket_name, key, _client=self.__client)

    def __str__(self) -> str:
        if self._key:
            return f"s3://{self._bucket_name}/{self._key}"
        return f"s3://{self._bucket_name}"

    def __repr__(self) -> str:
        return f"S3Path('{self}')"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, S3Path):
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
        return f"s3://{self._bucket_name}"

    @property
    def root(self) -> str:
        return "/"

    @property
    def anchor(self) -> str:
        return f"s3://{self._bucket_name}/"

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
    def parent(self) -> "S3Path":
        if "/" in self._key:
            return self._child("/".join(self._key.split("/")[:-1]))
        return self._child("")

    @property
    def parents(self) -> list["S3Path"]:
        parts = self._key.split("/") if self._key else []
        result = []
        for i in range(len(parts) - 1, -1, -1):
            result.append(self._child("/".join(parts[:i])))
        return result

    @property
    def parts(self) -> tuple[str, ...]:
        root = f"s3://{self._bucket_name}/"
        if not self._key:
            return (root,)
        return (root,) + tuple(self._key.split("/"))

    def __truediv__(self, other: str) -> "S3Path":
        other = str(other).strip("/")
        new_key = f"{self._key}/{other}" if self._key else other
        return self._child(new_key)

    def joinpath(self, *others: str) -> "S3Path":
        result = self
        for part in others:
            result = result / part
        return result

    def with_name(self, name: str) -> "S3Path":
        if not self._key:
            raise ValueError("S3Path has no name component")
        parent_key = "/".join(self._key.split("/")[:-1])
        new_key = f"{parent_key}/{name}" if parent_key else name
        return self._child(new_key)

    def with_stem(self, stem: str) -> "S3Path":
        return self.with_name(stem + self.suffix)

    def with_suffix(self, suffix: str) -> "S3Path":
        if suffix and not suffix.startswith("."):
            raise ValueError(f"Invalid suffix: {suffix!r}")
        return self.with_name(self.stem + suffix)

    def is_absolute(self) -> bool:
        return True

    def resolve(self, strict: bool = False) -> "S3Path":
        return self._child(self._key)

    def absolute(self) -> "S3Path":
        return self._child(self._key)

    def _object_exists(self) -> bool:
        import botocore.exceptions

        try:
            self._client.head_object(Bucket=self._bucket_name, Key=self._key)
            return True
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def _has_children(self, prefix: str) -> bool:
        res = self._client.list_objects_v2(
            Bucket=self._bucket_name, Prefix=prefix, MaxKeys=1
        )
        return bool(res.get("Contents") or res.get("CommonPrefixes"))

    def exists(self) -> bool:
        if not self._key:
            try:
                self._client.head_bucket(Bucket=self._bucket_name)
                return True
            except Exception:
                return False
        if self._object_exists():
            return True
        return self._has_children(self._key.rstrip("/") + "/")

    def is_file(self) -> bool:
        return bool(self._key) and self._object_exists()

    def is_dir(self) -> bool:
        if not self._key:
            return self.exists()
        if self._object_exists():
            return False
        return self._has_children(self._key.rstrip("/") + "/")

    def samefile(self, other: "CloudPath") -> bool:
        if not isinstance(other, S3Path):
            return False
        return self._bucket_name == other._bucket_name and self._key == other._key

    def iterdir(self) -> Iterator["S3Path"]:
        prefix = (self._key.rstrip("/") + "/") if self._key else ""
        seen: set[str] = set()
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=self._bucket_name, Prefix=prefix, Delimiter="/"
        ):
            for obj in page.get("Contents", []):
                rel = obj["Key"][len(prefix) :]
                top = rel.split("/")[0]
                if top and top not in seen:
                    seen.add(top)
                    yield self._child(prefix + top)
            for cp in page.get("CommonPrefixes", []):
                rel = cp["Prefix"][len(prefix) :].rstrip("/")
                if rel and rel not in seen:
                    seen.add(rel)
                    yield self._child(prefix + rel)

    def glob(self, pattern: str) -> Iterator["S3Path"]:
        import fnmatch

        prefix = (self._key.rstrip("/") + "/") if self._key else ""
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket_name, Prefix=prefix):
            for obj in page.get("Contents", []):
                rel = obj["Key"][len(prefix) :]
                if fnmatch.fnmatch(rel, pattern):
                    yield self._child(obj["Key"])

    def rglob(self, pattern: str) -> Iterator["S3Path"]:
        import fnmatch

        prefix = (self._key.rstrip("/") + "/") if self._key else ""
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket_name, Prefix=prefix):
            for obj in page.get("Contents", []):
                rel = obj["Key"][len(prefix) :]
                if fnmatch.fnmatch(rel, "**/" + pattern) or fnmatch.fnmatch(
                    rel, pattern
                ):
                    yield self._child(obj["Key"])

    def walk(
        self,
        top_down: bool = True,
        on_error: Any = None,
    ) -> Generator[tuple["S3Path", list[str], list[str]], None, None]:
        from collections import defaultdict

        prefix = (self._key.rstrip("/") + "/") if self._key else ""
        tree: dict[str, tuple[list[str], list[str]]] = defaultdict(lambda: ([], []))
        tree[self._key]

        try:
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._bucket_name, Prefix=prefix):
                for obj in page.get("Contents", []):
                    rel = obj["Key"][len(prefix) :]
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
        ) -> Generator[tuple["S3Path", list[str], list[str]], None, None]:
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
            data = self.read_bytes()
            buf = io.BytesIO(data)
            if mode == "r":
                return io.TextIOWrapper(
                    buf,
                    encoding=encoding or "utf-8",
                    errors=errors,
                    newline=newline,
                )
            return buf
        if mode in ("wb", "w"):
            return _S3WriteBuffer(
                self._client,
                self._bucket_name,
                self._key,
                binary=mode == "wb",
                encoding=encoding or "utf-8",
                errors=errors,
                newline=newline,
            )
        raise ValueError(f"Unsupported mode: {mode!r}")

    def read_bytes(self) -> bytes:
        res = self._client.get_object(Bucket=self._bucket_name, Key=self._key)
        return res["Body"].read()

    def read_text(self, encoding: str = "utf-8") -> str:
        return self.read_bytes().decode(encoding)

    def write_bytes(self, data: bytes) -> int:
        self._client.put_object(Bucket=self._bucket_name, Key=self._key, Body=data)
        return len(data)

    def write_text(self, data: str, encoding: str = "utf-8") -> int:
        encoded = data.encode(encoding)
        self._client.put_object(Bucket=self._bucket_name, Key=self._key, Body=encoded)
        return len(encoded)

    def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
        if self._object_exists():
            if not exist_ok:
                raise FileExistsError(str(self))
            return
        self._client.put_object(Bucket=self._bucket_name, Key=self._key, Body=b"")

    def unlink(self, missing_ok: bool = False) -> None:
        if not self._object_exists():
            if missing_ok:
                return
            raise FileNotFoundError(str(self))
        self._client.delete_object(Bucket=self._bucket_name, Key=self._key)

    def rename(self, target: "S3Path | str") -> "S3Path":
        if isinstance(target, str):
            target = S3Path.from_uri(target)
        self._client.copy_object(
            Bucket=target._bucket_name,
            Key=target._key,
            CopySource={"Bucket": self._bucket_name, "Key": self._key},
        )
        self._client.delete_object(Bucket=self._bucket_name, Key=self._key)
        return target

    def replace(self, target: "S3Path | str") -> "S3Path":
        return self.rename(target)

    def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None:
        if self.exists():
            if exist_ok:
                return
            raise FileExistsError(str(self))
        placeholder = self._key.rstrip("/") + "/"
        self._client.put_object(Bucket=self._bucket_name, Key=placeholder, Body=b"")

    def rmdir(self) -> None:
        placeholder = self._key.rstrip("/") + "/"
        import botocore.exceptions

        try:
            self._client.head_object(Bucket=self._bucket_name, Key=placeholder)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(str(self))
            raise
        res = self._client.list_objects_v2(
            Bucket=self._bucket_name, Prefix=placeholder, MaxKeys=2
        )
        children = [o for o in res.get("Contents", []) if o["Key"] != placeholder]
        if children:
            raise OSError(f"Directory not empty: {self}")
        self._client.delete_object(Bucket=self._bucket_name, Key=placeholder)

    def stat(self, follow_symlinks: bool = True) -> "S3StatResult":
        res = self._client.head_object(Bucket=self._bucket_name, Key=self._key)
        return S3StatResult(res)

    @classmethod
    def from_uri(cls, uri: str, _client=None) -> "S3Path":
        if not uri.startswith("s3://"):
            raise ValueError(f"Not an S3 URI: {uri!r}")
        without_scheme = uri[5:]
        parts = without_scheme.split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return cls(bucket, key, _client=_client)


class _S3WriteBuffer(io.RawIOBase):
    def __init__(self, client, bucket, key, binary, encoding, errors, newline):
        self._client = client
        self._bucket = bucket
        self._key = key
        self._binary = binary
        self._encoding = encoding
        self._errors = errors
        self._newline = newline
        self._buf = io.BytesIO()
        self._text_wrapper = None
        if not binary:
            self._text_wrapper = io.TextIOWrapper(
                self._buf, encoding=encoding, errors=errors, newline=newline
            )

    def write(self, data) -> int:
        if self._text_wrapper:
            return self._text_wrapper.write(data)
        return self._buf.write(data)

    def close(self) -> None:
        if not self.closed:
            if self._text_wrapper:
                self._text_wrapper.flush()
            self._buf.seek(0)
            self._client.put_object(
                Bucket=self._bucket, Key=self._key, Body=self._buf.read()
            )
        super().close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class S3StatResult:
    def __init__(self, head_response: dict):
        self._res = head_response

    @property
    def st_size(self) -> int:
        return self._res.get("ContentLength", 0)

    @property
    def st_mtime(self) -> float:
        dt = self._res.get("LastModified")
        return dt.timestamp() if dt else 0.0

    @property
    def st_ctime(self) -> float:
        return self.st_mtime

    def __repr__(self) -> str:
        return (
            f"S3StatResult(st_size={self.st_size}, "
            f"st_mtime={self.st_mtime}, st_ctime={self.st_ctime})"
        )
