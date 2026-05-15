import os

GCS_BUCKET = os.environ.get("CLOUDFS_TEST_GCS_BUCKET")
S3_BUCKET = os.environ.get("CLOUDFS_TEST_S3_BUCKET")
AZURE_CONTAINER = os.environ.get("CLOUDFS_TEST_AZURE_CONTAINER")
TEST_PREFIX = os.environ.get("CLOUDFS_TEST_PREFIX", "cloudfs-test")


def pytest_configure(config):
    config.addinivalue_line("markers", "gcs: requires CLOUDFS_TEST_GCS_BUCKET")
    config.addinivalue_line("markers", "s3: requires CLOUDFS_TEST_S3_BUCKET")
    config.addinivalue_line("markers", "azure: requires CLOUDFS_TEST_AZURE_CONTAINER")
