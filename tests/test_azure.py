"""Azure Blob Storage backend conformance and Azure-specific tests."""

import pytest

from tests.conformance import CloudPathConformance
from tests.conftest import AZURE_CONTAINER, TEST_PREFIX

pytestmark = pytest.mark.skipif(
    not AZURE_CONTAINER, reason="CLOUDFS_TEST_AZURE_CONTAINER not set"
)


class TestAzureConformance(CloudPathConformance):
    def _make_root(self, prefix: str):
        from cloudfs.backend.azure import AzurePath

        return AzurePath(AZURE_CONTAINER, prefix)


class TestAzureSpecific:
    """Tests for Azure-specific behavior not covered by the conformance suite."""

    def test_from_uri(self):
        from cloudfs.backend.azure import AzurePath

        p = AzurePath.from_uri(f"az://{AZURE_CONTAINER}/{TEST_PREFIX}/from_uri.txt")
        assert p._container_name == AZURE_CONTAINER
        assert p.name == "from_uri.txt"

    def test_path_dispatch(self):
        from cloudfs import Path
        from cloudfs.backend.azure import AzurePath

        p = Path(f"az://{AZURE_CONTAINER}/{TEST_PREFIX}/dispatch.txt")
        assert isinstance(p, AzurePath)
        assert isinstance(p, Path)
        assert type(p) is AzurePath
