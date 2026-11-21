"""File utilities - atomic writes and file locking."""

from __future__ import annotations

import locale
import os
import secrets
import stat
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

try:
    import fcntl

    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False
    import msvcrt


_THREAD_LOCKS: dict[Path, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _thread_lock_for(path: Path) -> threading.Lock:
    resolved = path.resolve()
    with _THREAD_LOCKS_GUARD:
        if resolved not in _THREAD_LOCKS:
            _THREAD_LOCKS[resolved] = threading.Lock()
        return _THREAD_LOCKS[resolved]


def atomic_write(
    path: Path, content: str, encoding: str | None = "utf-8", new_mode: int = 0o600
) -> None:
    """Write content atomically: a hidden temp file in the same folder, then os.replace().

    The contract:
    1. The final path only ever holds the whole new content or the whole old content.
    2. The temp file is never more readable than the final file, at any moment: it is
       created with its final mode in os.open itself.
    3. An existing file keeps its exact permission bits.
    4. A new file is created with ``new_mode`` (narrowed by the umask): private 0600 by
       default, as mkstemp made them; transcripts pass 0o666, as write_text gave them.
    5. Buffered write, flush, fsync, then os.replace; the temp is removed on any failure.

    ``encoding=None`` means the platform default, the one ``write_text`` and ``read_text``
    use without an encoding.
    """
    data = content.encode(encoding or locale.getpreferredencoding(False))
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = stat.S_IMODE(os.stat(path).st_mode)
    except FileNotFoundError:
        existing = None
    mode = new_mode if existing is None else existing
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    fd = os.open(tmp, flags, mode)  # outside the try: a name we did not create is never unlinked
    try:
        if existing is not None:
            os.chmod(tmp, mode)  # undo the umask's narrowing, before any byte; never wider
        with os.fdopen(fd, "wb") as f:
            fd = None  # the file object owns it now
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


@contextmanager
def file_lock(path: Path) -> Generator[None, None, None]:
    """Exclusive file lock for coordinated writes."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    thread_lock = _thread_lock_for(lock_path)

    if not _HAS_FCNTL:
        with thread_lock:
            with open(lock_path, "a+b") as lock_file:
                lock_file.seek(0)
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        return

    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT)
    try:
        with thread_lock:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
