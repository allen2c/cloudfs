# CloudFS

Cloud storage that works like your local filesystem.

CloudFS gives you a `pathlib.Path`-compatible interface for Google Cloud Storage, AWS S3, and Azure Blob Storage.

## Installation

```bash
pip install "cloudfs[google]"   # Google Cloud Storage
pip install "cloudfs[s3]"       # AWS S3
pip install "cloudfs[azure]"    # Azure Blob Storage
pip install "cloudfs[all]"      # All backends
```

## Quick Start

```python
from cloudfs import Path

# Works the same across all backends
p = Path("gs://my-bucket/data/report.csv")    # GCS
p = Path("s3://my-bucket/data/report.csv")    # S3
p = Path("az://my-container/data/report.csv") # Azure

p.write_text("Hello, CloudFS!")
print(p.read_text())            # Hello, CloudFS!
print(p.name)                   # report.csv
print(p.parent / "other.csv")  # gs://my-bucket/data/other.csv

for child in p.parent.iterdir():
    print(child)
```

## Documentation

Full documentation at **[allen2c.github.io/cloudfs](https://allen2c.github.io/cloudfs/)**.

## License

Apache 2.0
