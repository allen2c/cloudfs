"""GCS backend conformance and GCS-specific tests."""

import pytest

from tests.conformance import CloudPathConformance
from tests.conftest import GCS_BUCKET, TEST_PREFIX

pytestmark = pytest.mark.skipif(
    not GCS_BUCKET, reason="CLOUDFS_TEST_GCS_BUCKET not set"
)


class TestGCSConformance(CloudPathConformance):
    def _make_root(self, prefix: str):
        from cloudfs.backend.gcs import GCSPath

        return GCSPath(GCS_BUCKET, prefix)


class TestGCSSpecific:
    """Tests for GCS-specific behavior not covered by the conformance suite."""

    def test_from_uri(self):
        from cloudfs.backend.gcs import GCSPath

        p = GCSPath.from_uri(f"gs://{GCS_BUCKET}/{TEST_PREFIX}/from_uri.txt")
        assert p._bucket_name == GCS_BUCKET
        assert p.name == "from_uri.txt"

    def test_path_dispatch(self):
        from cloudfs import Path
        from cloudfs.backend.gcs import GCSPath

        p = Path(f"gs://{GCS_BUCKET}/{TEST_PREFIX}/dispatch.txt")
        assert isinstance(p, GCSPath)
        assert isinstance(p, Path)
        assert type(p) is GCSPath

    def test_unsupported_scheme(self):
        from cloudfs import Path

        with pytest.raises(ValueError):
            Path("azure://bucket/key")
