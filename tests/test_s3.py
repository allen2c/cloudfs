"""S3 backend conformance and S3-specific tests."""

import pytest
from dotenv import load_dotenv

load_dotenv()

from cloudfs.backend.s3 import S3Path  # noqa: E402
from tests.conformance import CloudPathConformance  # noqa: E402

BUCKET = "test-cloudfs-062984976919-ap-northeast-3-an"
PREFIX = "cloudfs-test"


class TestS3Conformance(CloudPathConformance):
    @pytest.fixture
    def root(self) -> S3Path:
        return S3Path(BUCKET, PREFIX)


class TestS3Specific:
    """Tests for S3-specific behavior not covered by the conformance suite."""

    def test_from_uri(self):
        p = S3Path.from_uri(f"s3://{BUCKET}/{PREFIX}/from_uri.txt")
        assert p._bucket_name == BUCKET
        assert p.name == "from_uri.txt"

    def test_path_dispatch(self):
        from cloudfs import Path

        p = Path(f"s3://{BUCKET}/{PREFIX}/dispatch.txt")
        assert isinstance(p, S3Path)
        assert isinstance(p, Path)
        assert type(p) is S3Path
