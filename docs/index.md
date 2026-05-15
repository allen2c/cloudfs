# CloudFS

Cloud storage that works like your local filesystem.

CloudFS gives you a `pathlib.Path`-compatible interface for Google Cloud Storage,
AWS S3, and Azure Blob Storage — so you can read, write, list, and move files
across cloud providers using the same API you already know.

```python
from cloudfs import Path

p = Path("gs://my-bucket/data/report.csv")
text = p.read_text()

for f in p.parent.iterdir():
    print(f.name)
```

## Features

- `pathlib.Path`-compatible API — no new interface to learn
- Supports **Google Cloud Storage**, **AWS S3**, and **Azure Blob Storage**
- Single `Path()` entry point — URI scheme selects the backend automatically
- `isinstance(p, Path)` works as expected

## Supported Backends

| Backend | URI Scheme | Install |
|---------|-----------|---------|
| Google Cloud Storage | `gs://bucket/key` | `pip install "cloudfs[google]"` |
| AWS S3 | `s3://bucket/key` | `pip install "cloudfs[s3]"` |
| Azure Blob Storage | `az://container/blob` | `pip install "cloudfs[azure]"` |

---

[Get started →](getting-started.md)
