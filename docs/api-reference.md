# API Reference

## `Path(uri)`

Entry point. Returns a backend-specific path object based on the URI scheme.

```python
from cloudfs import Path

p = Path("gs://bucket/key")    # → GCSPath
p = Path("s3://bucket/key")    # → S3Path
p = Path("az://container/key") # → AzurePath
```

`isinstance(p, Path)` returns `True` for all backends.

Raises `ValueError` for unsupported URI schemes.

---

## Properties

### `name → str`
The final component of the path.

```python
Path("gs://bucket/a/b/report.csv").name  # "report.csv"
```

### `stem → str`
The final component without its suffix.

```python
Path("gs://bucket/a/report.csv").stem  # "report"
```

### `suffix → str`
The file extension of the final component.

```python
Path("gs://bucket/a/report.csv").suffix  # ".csv"
```

### `suffixes → list[str]`
All extensions of the final component.

```python
Path("gs://bucket/a/archive.tar.gz").suffixes  # [".tar", ".gz"]
```

### `parent → Path`
The logical parent of the path.

```python
Path("gs://bucket/a/b/c.txt").parent  # gs://bucket/a/b
```

### `parents → list[Path]`
All logical ancestors.

### `parts → tuple[str, ...]`
The path split into components. The first element includes the URI scheme and bucket/container.

```python
Path("gs://bucket/a/b.txt").parts  # ("gs://bucket/", "a", "b.txt")
```

### `drive → str`
The URI scheme and bucket/container name.

```python
Path("gs://bucket/key").drive  # "gs://bucket"
```

### `root → str`
Always `"/"`.

### `anchor → str`
`drive + root`.

```python
Path("gs://bucket/key").anchor  # "gs://bucket/"
```

---

## Path Manipulation

### `path / other → Path`
Join paths using the `/` operator.

```python
p = Path("gs://bucket/data") / "2024" / "report.csv"
```

### `joinpath(*others) → Path`
Equivalent to chaining `/`.

### `with_name(name) → Path`
Return a new path with the filename changed.

```python
Path("gs://bucket/a/old.txt").with_name("new.txt")  # gs://bucket/a/new.txt
```

### `with_stem(stem) → Path`
Return a new path with the stem changed, preserving the suffix.

### `with_suffix(suffix) → Path`
Return a new path with the suffix changed.

```python
Path("gs://bucket/a/report.txt").with_suffix(".csv")  # gs://bucket/a/report.csv
```

### `is_absolute() → bool`
Always `True` — cloud paths are always absolute.

### `resolve(strict=False) → Path`
Returns a new path object equal to `self` (cloud paths are already absolute).

### `absolute() → Path`
Same as `resolve()`.

---

## Existence & Type Checks

### `exists() → bool`
`True` if the path refers to an existing file or directory.

### `is_file() → bool`
`True` if the path is an existing file (blob/object).

### `is_dir() → bool`
`True` if the path is a directory (has children or a placeholder blob).

### `samefile(other) → bool`
`True` if both paths point to the same object in the same bucket/container.

---

## Directory Listing

### `iterdir() → Iterator[Path]`
Yield the direct children of a directory (one level only).

### `glob(pattern) → Iterator[Path]`
Yield all matching paths using shell-style pattern matching.

```python
for f in Path("gs://bucket/data/").glob("*.csv"):
    print(f)
```

### `rglob(pattern) → Iterator[Path]`
Like `glob()` but recursive.

### `walk(top_down=True, on_error=None) → Generator`
Yield `(dirpath, dirnames, filenames)` tuples, similar to `os.walk()`.

---

## Reading & Writing

### `open(mode='r', encoding=None, errors=None, newline=None) → IO`
Open the file. Supports modes `'r'`, `'rb'`, `'w'`, `'wb'`.

```python
with p.open("r") as f:
    print(f.read())
```

### `read_bytes() → bytes`
Return the full contents as bytes.

### `read_text(encoding='utf-8') → str`
Return the full contents as a string.

### `write_bytes(data: bytes) → int`
Write bytes and return the number of bytes written.

### `write_text(data: str, encoding='utf-8') → int`
Write text and return the number of bytes written.

---

## File Operations

### `touch(mode=0o666, exist_ok=True) → None`
Create the file if it does not exist. If `exist_ok=False`, raises `FileExistsError` when the file already exists.

### `unlink(missing_ok=False) → None`
Delete the file. Raises `FileNotFoundError` if the file does not exist and `missing_ok=False`.

### `rename(target) → Path`
Move the file to `target` and return the new path.

### `replace(target) → Path`
Alias for `rename()`.

### `mkdir(parents=False, exist_ok=False) → None`
Create a directory placeholder. Raises `FileExistsError` if it already exists and `exist_ok=False`.

### `rmdir() → None`
Delete a directory placeholder created by `mkdir()`. Raises `FileNotFoundError` if the placeholder does not exist, and `OSError` if the directory is not empty.

### `stat(follow_symlinks=True) → StatResult`
Return an object with:

| Attribute | Type | Description |
|-----------|------|-------------|
| `st_size` | `int` | Size in bytes |
| `st_mtime` | `float` | Last modified (Unix timestamp) |
| `st_ctime` | `float` | Created time (Unix timestamp); falls back to `st_mtime` on backends that don't track creation time |

---

## Exceptions

### `CloudOperationError`

Raised when a `pathlib.Path` operation has no meaningful cloud equivalent.

```python
from cloudfs import CloudOperationError
```

Operations that always raise `CloudOperationError`:

- `is_symlink()`, `symlink_to()`, `hardlink_to()`
- `is_mount()`, `is_junction()`
- `is_block_device()`, `is_char_device()`, `is_fifo()`, `is_socket()`
- `lstat()`, `chmod()`, `lchmod()`
- `relative_to()`, `is_relative_to()`
- `expanduser()`, `home()`, `cwd()`
