"""Tests for atomic writes and file locking."""

import os
import stat
import sys
import threading

import pytest

from anyscribe.core.fileutil import atomic_write, file_lock


class TestAtomicWrite:
    def test_creates_file(self, tmp_path):
        p = tmp_path / "test.txt"
        atomic_write(p, "hello")
        assert p.read_text() == "hello"

    def test_overwrites_existing(self, tmp_path):
        p = tmp_path / "test.txt"
        p.write_text("old")
        atomic_write(p, "new")
        assert p.read_text() == "new"

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "a" / "b" / "test.txt"
        atomic_write(p, "nested")
        assert p.read_text() == "nested"

    def test_no_temp_file_left_on_success(self, tmp_path):
        p = tmp_path / "test.txt"
        atomic_write(p, "clean")
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == "test.txt"


def _mode(p) -> str:
    return oct(stat.S_IMODE(os.stat(p).st_mode))


def _write_under(umask, path, content="new", **kwargs):
    old = os.umask(umask)
    try:
        atomic_write(path, content, **kwargs)
    finally:
        os.umask(old)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
class TestAtomicWritePermissions:
    """The contract's permission rules, checked on the temp file during the call as well as
    on the final file after it: that is where a private file's content could leak."""

    def test_the_temp_file_is_never_wider_than_a_private_target(self, tmp_path, monkeypatch):
        target = tmp_path / "state.json"
        target.write_text("old")
        target.chmod(0o600)
        seen: dict[str, str] = {}

        def temp():
            (found,) = tmp_path.glob(".*.tmp")
            return found

        real_open, real_fdopen, real_fsync = os.open, os.fdopen, os.fsync

        def watched_open(file, flags, *a, **k):
            fd = real_open(file, flags, *a, **k)
            if str(file).endswith(".tmp"):
                seen["created"] = _mode(file)
            return fd

        def watched_fdopen(fd, *a, **k):
            seen["fdopen"] = _mode(temp())
            return real_fdopen(fd, *a, **k)

        def watched_fsync(fd):
            seen["fsync"] = _mode(temp())
            return real_fsync(fd)

        monkeypatch.setattr(os, "open", watched_open)
        monkeypatch.setattr(os, "fdopen", watched_fdopen)
        monkeypatch.setattr(os, "fsync", watched_fsync)
        _write_under(0o022, target)
        monkeypatch.undo()
        assert seen == {"created": "0o600", "fdopen": "0o600", "fsync": "0o600"}
        assert (target.read_text(), _mode(target)) == ("new", "0o600")

    def test_an_existing_private_file_stays_private(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("old")
        p.chmod(0o600)
        _write_under(0o022, p)
        assert (p.read_text(), _mode(p)) == ("new", "0o600")

    def test_an_existing_group_writable_file_keeps_its_bits(self, tmp_path):
        """Wider than the umask allows: the chmod after creation restores it exactly."""
        p = tmp_path / "shared.md"
        p.write_text("old")
        p.chmod(0o664)
        _write_under(0o022, p)
        assert (p.read_text(), _mode(p)) == ("new", "0o664")

    @pytest.mark.parametrize("umask", [0o022, 0o002])
    def test_a_new_file_is_private_by_default(self, tmp_path, umask):
        _write_under(umask, tmp_path / "new.json")
        assert _mode(tmp_path / "new.json") == "0o600"

    @pytest.mark.parametrize("umask, expected", [(0o022, "0o644"), (0o002, "0o664")])
    def test_new_mode_0o666_follows_the_umask(self, tmp_path, umask, expected):
        _write_under(umask, tmp_path / "new.md", new_mode=0o666)
        assert _mode(tmp_path / "new.md") == expected

    def test_a_failed_write_leaves_no_temp_file(self, tmp_path, monkeypatch):
        def broken_fsync(fd):
            raise OSError("disk gone")

        monkeypatch.setattr(os, "fsync", broken_fsync)
        with pytest.raises(OSError, match="disk gone"):
            atomic_write(tmp_path / "x.json", "data")
        monkeypatch.undo()
        assert os.listdir(tmp_path) == []


class TestFileLock:
    def test_lock_allows_sequential_access(self, tmp_path):
        p = tmp_path / "data.txt"
        p.write_text("0")

        with file_lock(p):
            val = int(p.read_text())
            atomic_write(p, str(val + 1))

        assert p.read_text() == "1"

    def test_lock_blocks_concurrent_access(self, tmp_path):
        p = tmp_path / "counter.txt"
        p.write_text("0")
        results = []

        def increment():
            with file_lock(p):
                val = int(p.read_text())
                results.append(val)
                atomic_write(p, str(val + 1))

        threads = [threading.Thread(target=increment) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # If locking works, final value should be 5
        assert p.read_text() == "5"
        # Each thread should have seen a unique value
        assert sorted(results) == [0, 1, 2, 3, 4]
