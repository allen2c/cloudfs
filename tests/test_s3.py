"""S3 backend conformance and S3-specific tests."""

import pytest

from tests.conformance import CloudPathConformance
from tests.conftest import S3_BUCKET, TEST_PREFIX

pytestmark = pytest.mark.skipif(not S3_BUCKET, reason="CLOUDFS_TEST_S3_BUCKET not set")


class TestS3Conformance(CloudPathConformance):
    def _make_root(self, prefix: str):
        from cloudfs.backend.s3 import S3Path

        return S3Path(S3_BUCKET, prefix)


class TestS3Specific:
    """Tests for S3-specific behavior not covered by the conformance suite."""

    def test_from_uri(self):
        from cloudfs.backend.s3 import S3Path

        p = S3Path.from_uri(f"s3://{S3_BUCKET}/{TEST_PREFIX}/from_uri.txt")
        assert p._bucket_name == S3_BUCKET
        assert p.name == "from_uri.txt"

    def test_path_dispatch(self):
        from cloudfs import Path
        from cloudfs.backend.s3 import S3Path

        p = Path(f"s3://{S3_BUCKET}/{TEST_PREFIX}/dispatch.txt")
        assert isinstance(p, S3Path)
        assert isinstance(p, Path)
        assert type(p) is S3Path
