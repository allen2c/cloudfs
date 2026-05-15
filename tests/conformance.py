"""Backend-agnostic conformance test suite for CloudPath implementations.

Any backend must pass all tests in CloudPathConformance to be considered compliant.
Subclass this and override the `root` fixture to plug in a backend.
"""

import pytest

from cloudfs import Path
from cloudfs.base import CloudPath
from cloudfs.exceptions import CloudOperationError


class CloudPathConformance:
    """Override `root` in subclass to provide a backend-specific base path."""

    @pytest.fixture
    def root(self) -> CloudPath:
        raise NotImplementedError("Subclasses must provide a `root` fixture.")

    def test_str_and_repr(self, root: CloudPath):
        assert isinstance(str(root), str)
        assert type(root).__name__ in repr(root)

    def test_truediv(self, root: CloudPath):
        p = root / "subdir" / "file.txt"
        assert p.name == "file.txt"
        assert p.stem == "file"
        assert p.suffix == ".txt"

    def test_parent(self, root: CloudPath):
        p = root / "a" / "b" / "c.txt"
        assert p.parent == root / "a" / "b"
        assert p.parent.parent == root / "a"

    def test_parts(self, root: CloudPath):
        p = root / "a" / "b.txt"
        assert p.parts[-1] == "b.txt"
        assert p.parts[-2] == "a"

    def test_drive_root_anchor(self, root: CloudPath):
        assert isinstance(root.drive, str) and root.drive
        assert root.root == "/"
        assert root.anchor == root.drive + "/"

    def test_is_absolute(self, root: CloudPath):
        assert root.is_absolute() is True

    def test_resolve_returns_copy(self, root: CloudPath):
        p = root / "file.txt"
        assert p.resolve() == p
        assert p.absolute() == p
        assert p.resolve() is not p

    def test_with_name(self, root: CloudPath):
        p = root / "a" / "old.txt"
        assert p.with_name("new.txt") == root / "a" / "new.txt"

    def test_with_stem(self, root: CloudPath):
        p = root / "a" / "old.txt"
        assert p.with_stem("new") == root / "a" / "new.txt"

    def test_with_suffix(self, root: CloudPath):
        p = root / "a" / "file.txt"
        assert p.with_suffix(".md") == root / "a" / "file.md"

    def test_ordering(self, root: CloudPath):
        a = root / "a.txt"
        b = root / "b.txt"
        assert a < b
        assert b > a
        assert a <= a
        assert a >= a

    def test_write_read_unlink(self, root: CloudPath):
        p = root / "hello.txt"
        p.write_text("hello cloudfs")
        assert p.is_file()
        assert p.read_text() == "hello cloudfs"
        p.unlink()
        assert not p.exists()

    def test_write_read_bytes(self, root: CloudPath):
        p = root / "bytes.bin"
        p.write_bytes(b"\x00\x01\x02")
        assert p.read_bytes() == b"\x00\x01\x02"
        p.unlink()

    def test_open_write_read(self, root: CloudPath):
        p = root / "open_test.txt"
        with p.open("w") as f:
            f.write("hello from open")
        with p.open("r") as f:
            assert f.read() == "hello from open"
        p.unlink()

    def test_touch(self, root: CloudPath):
        p = root / "touch_test.txt"
        p.touch()
        assert p.is_file()
        p.unlink()

    def test_is_dir(self, root: CloudPath):
        p = root / "dirtest" / "file.txt"
        p.write_text("x")
        assert (root / "dirtest").is_dir()
        assert not (root / "dirtest").is_file()
        p.unlink()

    def test_samefile(self, root: CloudPath):
        p = root / "file.txt"
        assert p.samefile(root / "file.txt") is True
        assert p.samefile(root / "other.txt") is False

    def test_iterdir(self, root: CloudPath):
        files = ["iter_a.txt", "iter_b.txt", "iter_c.txt"]
        for f in files:
            (root / f).write_text(f)
        children = {c.name for c in root.iterdir()}
        for f in files:
            assert f in children
        for f in files:
            (root / f).unlink()

    def test_glob(self, root: CloudPath):
        (root / "glob_x.txt").write_text("x")
        (root / "glob_y.txt").write_text("y")
        (root / "glob_z.csv").write_text("z")
        results = {p.name for p in root.glob("*.txt")}
        assert "glob_x.txt" in results
        assert "glob_y.txt" in results
        assert "glob_z.csv" not in results
        for name in ["glob_x.txt", "glob_y.txt", "glob_z.csv"]:
            (root / name).unlink()

    def test_walk(self, root: CloudPath):
        (root / "walk_dir" / "a.txt").write_text("a")
        (root / "walk_dir" / "sub" / "b.txt").write_text("b")
        results = list(root.walk())
        all_files = [f for _, _, files in results for f in files]
        assert "a.txt" in all_files
        assert "b.txt" in all_files
        (root / "walk_dir" / "a.txt").unlink()
        (root / "walk_dir" / "sub" / "b.txt").unlink()

    def test_rename(self, root: CloudPath):
        src = root / "rename_src.txt"
        dst = root / "rename_dst.txt"
        src.write_text("rename me")
        src.rename(dst)
        assert not src.exists()
        assert dst.read_text() == "rename me"
        dst.unlink()

    def test_stat(self, root: CloudPath):
        p = root / "stat_test.txt"
        p.write_text("stat content")
        s = p.stat()
        assert s.st_size > 0
        assert s.st_mtime > 0
        p.unlink()

    def test_unlink_missing_ok(self, root: CloudPath):
        p = root / "nonexistent.txt"
        p.unlink(missing_ok=True)

    def test_unlink_missing_raises(self, root: CloudPath):
        p = root / "nonexistent.txt"
        with pytest.raises(FileNotFoundError):
            p.unlink()

    def test_isinstance_path(self, root: CloudPath):
        assert isinstance(root, Path)

    def test_cloud_operation_errors(self, root: CloudPath):
        p = root / "file.txt"
        with pytest.raises(CloudOperationError):
            p.is_symlink()
        with pytest.raises(CloudOperationError):
            p.chmod(0o644)
        with pytest.raises(CloudOperationError):
            p.relative_to(root)
        with pytest.raises(CloudOperationError):
            type(p).home()
        with pytest.raises(CloudOperationError):
            type(p).cwd()
