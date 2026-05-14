"""Integration tests for GCSPath against a real GCS bucket."""

import pytest
from dotenv import load_dotenv

load_dotenv()

from cloudfs.backend.gcs import GCSPath

BUCKET = "test-cloudfs"
PREFIX = "cloudfs-test"


@pytest.fixture
def root() -> GCSPath:
    return GCSPath(BUCKET, PREFIX)


def test_str_and_repr(root: GCSPath):
    assert str(root) == f"gs://{BUCKET}/{PREFIX}"
    assert "GCSPath" in repr(root)


def test_truediv(root: GCSPath):
    p = root / "subdir" / "file.txt"
    assert str(p) == f"gs://{BUCKET}/{PREFIX}/subdir/file.txt"
    assert p.name == "file.txt"
    assert p.stem == "file"
    assert p.suffix == ".txt"


def test_parent(root: GCSPath):
    p = root / "a" / "b" / "c.txt"
    assert p.parent == root / "a" / "b"
    assert p.parent.parent == root / "a"


def test_parts(root: GCSPath):
    p = root / "a" / "b.txt"
    assert p.parts[-1] == "b.txt"
    assert p.parts[-2] == "a"


def test_write_read_unlink(root: GCSPath):
    p = root / "hello.txt"
    p.write_text("hello cloudfs")
    assert p.is_file()
    assert p.read_text() == "hello cloudfs"
    p.unlink()
    assert not p.exists()


def test_write_read_bytes(root: GCSPath):
    p = root / "bytes.bin"
    p.write_bytes(b"\x00\x01\x02")
    assert p.read_bytes() == b"\x00\x01\x02"
    p.unlink()


def test_is_dir(root: GCSPath):
    p = root / "dirtest" / "file.txt"
    p.write_text("x")
    assert (root / "dirtest").is_dir()
    assert not (root / "dirtest").is_file()
    p.unlink()


def test_iterdir(root: GCSPath):
    files = ["iter_a.txt", "iter_b.txt", "iter_c.txt"]
    for f in files:
        (root / f).write_text(f)
    children = {c.name for c in root.iterdir()}
    for f in files:
        assert f in children
    for f in files:
        (root / f).unlink()


def test_glob(root: GCSPath):
    (root / "glob_x.txt").write_text("x")
    (root / "glob_y.txt").write_text("y")
    (root / "glob_z.csv").write_text("z")
    results = {p.name for p in root.glob("*.txt")}
    assert "glob_x.txt" in results
    assert "glob_y.txt" in results
    assert "glob_z.csv" not in results
    for name in ["glob_x.txt", "glob_y.txt", "glob_z.csv"]:
        (root / name).unlink()


def test_rename(root: GCSPath):
    src = root / "rename_src.txt"
    dst = root / "rename_dst.txt"
    src.write_text("rename me")
    src.rename(dst)
    assert not src.exists()
    assert dst.read_text() == "rename me"
    dst.unlink()


def test_stat(root: GCSPath):
    p = root / "stat_test.txt"
    p.write_text("stat content")
    s = p.stat()
    assert s.st_size > 0
    assert s.st_mtime > 0
    p.unlink()


def test_from_uri():
    p = GCSPath.from_uri(f"gs://{BUCKET}/{PREFIX}/from_uri.txt")
    assert p._bucket_name == BUCKET
    assert p.name == "from_uri.txt"


def test_unlink_missing_ok(root: GCSPath):
    p = root / "nonexistent.txt"
    p.unlink(missing_ok=True)  # should not raise


def test_unlink_missing_raises(root: GCSPath):
    p = root / "nonexistent.txt"
    with pytest.raises(FileNotFoundError):
        p.unlink()
