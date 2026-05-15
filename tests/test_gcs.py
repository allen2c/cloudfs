"""GCS backend conformance and GCS-specific tests."""

import pytest
from dotenv import load_dotenv

load_dotenv()

from cloudfs.backend.gcs import GCSPath  # noqa: E402
from tests.conformance import CloudPathConformance  # noqa: E402

BUCKET = "test-cloudfs"
PREFIX = "cloudfs-test"


class TestGCSConformance(CloudPathConformance):
    @pytest.fixture
    def root(self) -> GCSPath:
        return GCSPath(BUCKET, PREFIX)


class TestGCSSpecific:
    """Tests for GCS-specific behavior not covered by the conformance suite."""

    @pytest.fixture
    def root(self) -> GCSPath:
        return GCSPath(BUCKET, PREFIX)

    def test_from_uri(self):
        p = GCSPath.from_uri(f"gs://{BUCKET}/{PREFIX}/from_uri.txt")
        assert p._bucket_name == BUCKET
        assert p.name == "from_uri.txt"

    def test_path_dispatch(self):
        from cloudfs import Path

        p = Path(f"gs://{BUCKET}/{PREFIX}/dispatch.txt")
        assert isinstance(p, GCSPath)
        assert isinstance(p, Path)
        assert type(p) is GCSPath

    def test_unsupported_scheme(self):
        from cloudfs import Path

        with pytest.raises(ValueError):
            Path("azure://bucket/key")
