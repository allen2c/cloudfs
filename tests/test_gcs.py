"""Integration tests for GCSPath against a real GCS bucket."""

import pytest
from dotenv import load_dotenv

load_dotenv()

from cloudfs import Path
from cloudfs.backend.gcs import GCSPath
from cloudfs.exceptions import CloudOperationError

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


def test_path_dispatch():
    p = Path(f"gs://{BUCKET}/{PREFIX}/dispatch.txt")
    assert isinstance(p, GCSPath)
    assert isinstance(p, Path)
    assert type(p) is GCSPath


def test_unsupported_scheme():
    with pytest.raises(ValueError):
        Path("s3://bucket/key")


def test_drive_root_anchor(root: GCSPath):
    assert root.drive == f"gs://{BUCKET}"
    assert root.root == "/"
    assert root.anchor == f"gs://{BUCKET}/"


def test_is_absolute(root: GCSPath):
    assert root.is_absolute() is True


def test_resolve_absolute_return_copy(root: GCSPath):
    p = root / "file.txt"
    assert p.resolve() == p
    assert p.absolute() == p
    assert p.resolve() is not p


def test_with_name(root: GCSPath):
    p = root / "a" / "old.txt"
    assert p.with_name("new.txt") == root / "a" / "new.txt"


def test_with_stem(root: GCSPath):
    p = root / "a" / "old.txt"
    assert p.with_stem("new") == root / "a" / "new.txt"


def test_with_suffix(root: GCSPath):
    p = root / "a" / "file.txt"
    assert p.with_suffix(".md") == root / "a" / "file.md"


def test_samefile(root: GCSPath):
    p = root / "file.txt"
    assert p.samefile(root / "file.txt") is True
    assert p.samefile(root / "other.txt") is False


def test_touch(root: GCSPath):
    p = root / "touch_test.txt"
    p.touch()
    assert p.is_file()
    p.unlink()


def test_open_write_read(root: GCSPath):
    p = root / "open_test.txt"
    with p.open("w") as f:
        f.write("hello from open")
    with p.open("r") as f:
        assert f.read() == "hello from open"
    p.unlink()


def test_walk(root: GCSPath):
    (root / "walk_dir" / "a.txt").write_text("a")
    (root / "walk_dir" / "sub" / "b.txt").write_text("b")

    results = list(root.walk())
    all_files = [f for _, _, files in results for f in files]
    assert "a.txt" in all_files
    assert "b.txt" in all_files

    (root / "walk_dir" / "a.txt").unlink()
    (root / "walk_dir" / "sub" / "b.txt").unlink()


def test_ordering(root: GCSPath):
    a = root / "a.txt"
    b = root / "b.txt"
    assert a < b
    assert b > a
    assert a <= a
    assert a >= a


def test_cloud_operation_error(root: GCSPath):
    p = root / "file.txt"
    with pytest.raises(CloudOperationError):
        p.is_symlink()
    with pytest.raises(CloudOperationError):
        p.chmod(0o644)
    with pytest.raises(CloudOperationError):
        p.relative_to(root)
    with pytest.raises(CloudOperationError):
        GCSPath.home()
    with pytest.raises(CloudOperationError):
        GCSPath.cwd()
