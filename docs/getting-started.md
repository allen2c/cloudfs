# Getting Started

## Installation

Install CloudFS with the backend(s) you need:

```bash
# Google Cloud Storage
pip install "cloudfs[google]"

# AWS S3
pip install "cloudfs[s3]"

# Azure Blob Storage
pip install "cloudfs[azure]"

# All backends
pip install "cloudfs[all]"
```

## Credentials

CloudFS uses each provider's standard credential mechanism — no extra configuration needed.

**Google Cloud Storage**

Set the path to your service account key:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

Or use [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials) via `gcloud auth application-default login`.

**AWS S3**

Set your access key in environment variables:

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=ap-northeast-1
```

Or configure via `aws configure` if you have the AWS CLI installed.

**Azure Blob Storage**

Set your connection string:

```bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
```

Find it in: Azure Portal → Storage Account → Access keys → Connection string.

## Quick Start

Create a `Path` by passing any supported URI — the backend is selected automatically:

```python
from cloudfs import Path

# Google Cloud Storage
p = Path("gs://my-bucket/data/hello.txt")

# AWS S3
p = Path("s3://my-bucket/data/hello.txt")

# Azure Blob Storage
p = Path("az://my-container/data/hello.txt")
```

### Read & Write

```python
from cloudfs import Path

p = Path("gs://my-bucket/notes/hello.txt")

# Write
p.write_text("Hello, CloudFS!")

# Read
print(p.read_text())  # Hello, CloudFS!

# Binary
p.write_bytes(b"\x00\x01\x02")
data = p.read_bytes()
```

### Large files (streaming)

`read_text`, `read_bytes`, `write_text`, and `write_bytes` load the whole object
into memory, exactly like `pathlib`. For large objects, use `open()` instead — it
streams in fixed-size chunks, so memory stays bounded no matter how big the object
is (writes use the backend's native multipart / block upload):

```python
src = Path("s3://my-bucket/big.bin")
dst = Path("gs://my-bucket/copy.bin")

# Stream-copy across backends without loading the whole object into memory
with src.open("rb") as r, dst.open("wb") as w:
    for chunk in iter(lambda: r.read(8 << 20), b""):  # 8 MiB at a time
        w.write(chunk)
```

This works the same across all three backends.

### Navigate

```python
p = Path("gs://my-bucket/data/2024/report.csv")

print(p.name)    # report.csv
print(p.stem)    # report
print(p.suffix)  # .csv
print(p.parent)  # gs://my-bucket/data/2024

# Join paths
p2 = p.parent / "summary.csv"
print(p2)        # gs://my-bucket/data/2024/summary.csv
```

### List & Glob

```python
base = Path("gs://my-bucket/data/")

# List direct children
for child in base.iterdir():
    print(child)

# Glob
for csv in base.glob("*.csv"):
    print(csv)

# Walk recursively
for dirpath, dirnames, filenames in base.walk():
    for f in filenames:
        print(dirpath / f)
```

### File operations

```python
p = Path("gs://my-bucket/tmp/file.txt")

p.touch()                     # create empty file
p.exists()                    # True
p.is_file()                   # True
p.unlink()                    # delete
p.unlink(missing_ok=True)     # delete, no error if missing

p.rename(p.with_name("new.txt"))   # move
```
