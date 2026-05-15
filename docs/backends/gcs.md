# Google Cloud Storage

## URI Format

```
gs://bucket-name/path/to/object
```

## Credentials

CloudFS uses [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials).

**Option 1 — Service account key file:**

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

**Option 2 — Application Default Credentials:**

```bash
gcloud auth application-default login
```

Required IAM role: `Storage Object Admin` (or `Storage Object Creator` + `Storage Object Viewer`).

## Usage

```python
from cloudfs import Path

p = Path("gs://my-bucket/data/report.csv")
p.write_text("hello")
print(p.read_text())
```

## Caveats

**Directories are virtual.** GCS has no real directories — only object names containing slashes.

- `mkdir()` creates a zero-byte placeholder object (`prefix/`). If you delete all files under a directory but the placeholder remains, `is_dir()` still returns `True`.
- Writing directly to a sub-path never requires a prior `mkdir()`.
- A path can simultaneously satisfy `is_file()` and `is_dir()` if a blob named `foo` and another named `foo/bar` both exist.

**`rmdir()` only removes placeholder blobs.** A "virtual" directory that was never explicitly created via `mkdir()` will raise `FileNotFoundError` from `rmdir()` even if `is_dir()` returns `True`.

**Performance.** Each `exists()`, `is_file()`, and `is_dir()` call makes at least one API request. Prefer `iterdir()` or `walk()` for bulk operations.
