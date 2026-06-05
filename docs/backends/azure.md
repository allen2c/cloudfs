# Azure Blob Storage

## URI Format

```
az://container-name/path/to/blob
```

## Credentials

Set the connection string from your storage account:

```bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
```

Find it in: **Azure Portal → Storage Account → Access keys → Connection string**.

Ensure **Allow storage account key access** is enabled under **Settings → Configuration**, and that **Public network access** is set to **Enabled from all networks** (or your IP is allowlisted).

## Usage

```python
from cloudfs import Path

p = Path("az://my-container/data/report.csv")
p.write_text("hello")
print(p.read_text())
```

## Caveats

**Directories are virtual.** Azure Blob Storage has no real directories — only blob names containing slashes.

- `mkdir()` creates a zero-byte placeholder blob (`prefix/`). If you delete all files under a directory but the placeholder remains, `is_dir()` still returns `True`.
- Writing directly to a sub-path never requires a prior `mkdir()`.
- A path can simultaneously satisfy `is_file()` and `is_dir()` if a blob named `foo` and another named `foo/bar` both exist.

**`rmdir()` only removes placeholder blobs.** A "virtual" directory that was never explicitly created via `mkdir()` will raise `FileNotFoundError` from `rmdir()` even if `is_dir()` returns `True`.

**`rename()` is not atomic.** It is implemented as copy + delete. A crash between the two steps leaves both source and destination in place.

**`open()` streams; `read_bytes`/`write_bytes` don't.** `open("rb")` and `open("wb")` stream the blob in fixed-size chunks — writes stage blocks and commit them on `close()`, so memory stays bounded regardless of blob size. Use them for large blobs. `read_bytes`/`write_bytes`/`read_text`/`write_text` load the whole blob into memory, matching `pathlib` semantics. See [Getting Started → Large files](../getting-started.md#large-files-streaming).

**Performance.** Each `exists()`, `is_file()`, and `is_dir()` call makes at least one API request. Prefer `iterdir()` or `walk()` for bulk operations.
