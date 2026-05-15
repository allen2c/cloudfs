"""Azure Blob Storage backend conformance and Azure-specific tests."""

import pytest
from dotenv import load_dotenv

load_dotenv()

from cloudfs.backend.azure import AzurePath  # noqa: E402
from tests.conformance import CloudPathConformance  # noqa: E402

CONTAINER = "test-cloudfs"
PREFIX = "cloudfs-test"


class TestAzureConformance(CloudPathConformance):
    @pytest.fixture
    def root(self) -> AzurePath:
        return AzurePath(CONTAINER, PREFIX)


class TestAzureSpecific:
    """Tests for Azure-specific behavior not covered by the conformance suite."""

    def test_from_uri(self):
        p = AzurePath.from_uri(f"az://{CONTAINER}/{PREFIX}/from_uri.txt")
        assert p._container_name == CONTAINER
        assert p.name == "from_uri.txt"

    def test_path_dispatch(self):
        from cloudfs import Path

        p = Path(f"az://{CONTAINER}/{PREFIX}/dispatch.txt")
        assert isinstance(p, AzurePath)
        assert isinstance(p, Path)
        assert type(p) is AzurePath
