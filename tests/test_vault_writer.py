"""Tests for vault/writer.py — transcript writing, slugify, collisions."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from anyscribe.config.settings import Settings
from anyscribe.downloaders.base import DownloadResult
from anyscribe.providers.base import TranscriptResult, TranscriptSegment
from anyscribe.vault.writer import slugify, write_transcript


def make_download(**overrides) -> DownloadResult:
    defaults = dict(
        audio_path=Path("/tmp/does-not-matter.mp3"),
        title="My Test Video",
        duration=90.0,
        platform="youtube",
        original_url="https://www.youtube.com/watch?v=abc123",
        channel="Some Channel",
    )
    defaults.update(overrides)
    return DownloadResult(**defaults)


def make_transcript(**overrides) -> TranscriptResult:
    defaults = dict(text="hello world this is a transcript", language="en")
    defaults.update(overrides)
    return TranscriptResult(**defaults)


def test_write_transcript_frontmatter_keys(tmp_path: Path) -> None:
    download = make_download()
    transcript = make_transcript()
    settings = Settings(provider="openai")

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)
    content = out_path.read_text()

    assert content.startswith("---\n")
    assert "source: https://www.youtube.com/watch?v=abc123" in content
    assert "platform: youtube" in content
    assert 'title: "My Test Video"' in content
    assert "language: en" in content
    assert "provider: openai" in content
    assert f"word_count: {transcript.word_count}" in content
    assert "- transcript" in content
    assert "- youtube" in content
    # diarize is False by default — key should be absent
    assert "diarized: true" not in content


def test_write_transcript_diarized_flag_in_frontmatter(tmp_path: Path) -> None:
    download = make_download()
    transcript = make_transcript()
    settings = Settings(diarize=True)

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)
    content = out_path.read_text()

    assert "diarized: true" in content


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Hello World", "hello-world"),
        ("  spaces   everywhere  ", "spaces-everywhere"),
        ("Ünïcödé Tîtlé", "ünïcödé-tîtlé"),  # \w is unicode-aware — accented letters kept
        ("", ""),
        ("!!!", ""),
    ],
)
def test_slugify_edge_cases(text: str, expected: str) -> None:
    assert slugify(text) == expected


def test_slugify_emoji_strips_to_empty() -> None:
    # emoji are non-word chars under \w, so they're stripped entirely
    assert slugify("\U0001f600\U0001f601") == ""


def test_write_transcript_empty_title_falls_back_to_untitled(tmp_path: Path) -> None:
    """slugify('') == '' — writer.py falls back to the literal 'untitled' slug."""
    download = make_download(title="!!!")
    transcript = make_transcript()
    settings = Settings()

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)

    assert out_path.name == "untitled.md"


def test_write_transcript_slug_collision_appends_counter(tmp_path: Path) -> None:
    download = make_download(title="Same Title")
    transcript = make_transcript()
    settings = Settings()

    first = write_transcript(download, transcript, settings, workspace=tmp_path)
    second = write_transcript(download, transcript, settings, workspace=tmp_path)
    third = write_transcript(download, transcript, settings, workspace=tmp_path)

    assert first.name == "same-title.md"
    assert second.name == "same-title-2.md"
    assert third.name == "same-title-3.md"


def test_write_transcript_clean_format_has_plain_text_body(tmp_path: Path) -> None:
    segments = [
        TranscriptSegment(id=0, start=0.0, end=2.0, text="hello"),
        TranscriptSegment(id=1, start=2.0, end=4.0, text="world"),
    ]
    download = make_download()
    transcript = make_transcript(text="hello world", segments=segments)
    settings = Settings(output_format="clean")

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)
    content = out_path.read_text()

    assert "## Transcript\n\nhello world" in content
    assert "[00:00]" not in content


def test_write_transcript_timestamped_format(tmp_path: Path) -> None:
    segments = [
        TranscriptSegment(id=0, start=0.0, end=2.0, text="hello"),
        TranscriptSegment(id=1, start=65.0, end=68.0, text="world"),
    ]
    download = make_download()
    transcript = make_transcript(text="hello world", segments=segments)
    settings = Settings(output_format="timestamped")

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)
    content = out_path.read_text()

    assert "**[0:00]** hello" in content
    assert "**[1:05]** world" in content


def test_write_transcript_diarized_format_groups_by_speaker(tmp_path: Path) -> None:
    segments = [
        TranscriptSegment(id=0, start=0.0, end=2.0, text="hi there", speaker="Speaker 0"),
        TranscriptSegment(id=1, start=2.0, end=4.0, text="how are you", speaker="Speaker 0"),
        TranscriptSegment(id=2, start=5.0, end=7.0, text="good thanks", speaker="Speaker 1"),
    ]
    download = make_download()
    transcript = make_transcript(text="hi there how are you good thanks", segments=segments)
    settings = Settings(output_format="diarized")

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)
    content = out_path.read_text()

    assert "**Speaker 0** *[0:00]*: hi there how are you" in content
    assert "**Speaker 1** *[0:05]*: good thanks" in content


def test_write_transcript_diarized_format_without_speakers_falls_back_to_timestamped(
    tmp_path: Path,
) -> None:
    segments = [TranscriptSegment(id=0, start=0.0, end=2.0, text="no speaker data")]
    download = make_download()
    transcript = make_transcript(text="no speaker data", segments=segments)
    settings = Settings(output_format="diarized")

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)
    content = out_path.read_text()

    assert "**[0:00]** no speaker data" in content


_SHORT_WRITE = """
import errno, json, resource, sys
from pathlib import Path

from anyscribe.config.settings import Settings
from anyscribe.core.fileutil import atomic_write
from anyscribe.downloaders.base import DownloadResult
from anyscribe.providers.base import TranscriptResult
from anyscribe.vault.writer import write_transcript

folder = Path(sys.argv[1])
# The kernel accepts the first 64 KB of a write past this size, then refuses: a real short write.
resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024, resource.getrlimit(resource.RLIMIT_FSIZE)[1]))
seen = {}
for name, write in [
    ("file", lambda: atomic_write(folder / "file" / "t.md", "x" * 1024 * 1024)),
    ("transcript", lambda: write_transcript(
        DownloadResult(audio_path=Path("/nonexistent.mp3"), title="Big Talk", duration=90.0,
                       platform="youtube", original_url="https://www.youtube.com/watch?v=big"),
        TranscriptResult(text="word " * 250_000, language="en"),
        Settings(), workspace=folder / "vault")),
]:
    try:
        write()
        seen[name] = "no error"
    except OSError as e:
        seen[name] = errno.errorcode.get(e.errno, str(e.errno))
print(json.dumps(seen))
"""


@pytest.mark.skipif(sys.platform == "win32", reason="RLIMIT_FSIZE is POSIX only")
def test_a_short_write_never_reaches_the_final_path(tmp_path: Path, monkeypatch) -> None:
    """Invariant: a transcript's final path only ever holds the whole content (or what it held
    before). A real short write, from the kernel's file-size limit, must raise and publish
    nothing: not a cut-off file, which duplicate detection would take as already done."""
    import json
    import subprocess

    from anyscribe.core import dedup

    (tmp_path / "file").mkdir()
    (tmp_path / "file" / "t.md").write_text("old")
    done = subprocess.run(
        [sys.executable, "-c", _SHORT_WRITE, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    errors = json.loads(done.stdout)
    # Over a file holding "old": the error, what the file holds, every name in its folder.
    file_dir = tmp_path / "file"
    assert (errors["file"], (file_dir / "t.md").read_text(), sorted(os.listdir(file_dir))) == (
        "EFBIG",
        "old",
        ["t.md"],
    )
    # A new transcript: the error, and nothing at all in its folder.
    ws = tmp_path / "vault"
    out_dir = ws / "sources" / "youtube"
    assert (errors["transcript"], sorted(os.listdir(out_dir))) == ("EFBIG", [])
    monkeypatch.setattr(dedup, "get_workspace_dir", lambda: ws)
    assert dedup.find_existing_transcript("https://www.youtube.com/watch?v=big") is None


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
@pytest.mark.parametrize("umask, expected", [(0o022, "0o644"), (0o002, "0o664")])
def test_a_transcript_gets_the_same_permissions_as_write_text(
    tmp_path: Path, umask, expected
) -> None:
    """The atomic write must not make transcripts owner-only: same bits as write_text."""
    old = os.umask(umask)
    try:
        out = write_transcript(make_download(), make_transcript(), Settings(), workspace=tmp_path)
        plain = tmp_path / "plain.md"
        plain.write_text("x")
    finally:
        os.umask(old)
    assert (oct(out.stat().st_mode & 0o777), oct(plain.stat().st_mode & 0o777)) == (
        expected,
        expected,
    )


def test_transcript_keeps_the_platform_encoding(tmp_path: Path, monkeypatch) -> None:
    """The atomic write must not change the encoding: transcripts are read back with the
    platform default (History, MCP, duplicate detection), so they are written with it too,
    exactly as Path.write_text did before."""
    import locale

    title = "Café Crème à la mode"
    out = write_transcript(
        make_download(title=title), make_transcript(), Settings(), workspace=tmp_path / "a"
    )
    ref = tmp_path / "ref.md"
    # What write_text produces under the current locale. newline="\n": write_text wrote \r\n on
    # Windows; every reader opens in text mode, which reads both the same.
    text = out.read_text()  # the transcript as text, kept before the encoding changes below
    ref.write_text(text, newline="\n")
    assert out.read_bytes() == ref.read_bytes()

    # A Windows code page: the writer must follow it, not force UTF-8.
    monkeypatch.setattr(locale, "getpreferredencoding", lambda do_setlocale=True: "cp1252")
    cp = write_transcript(
        make_download(title=title), make_transcript(), Settings(), workspace=tmp_path / "b"
    )
    assert cp.read_bytes() == text.encode("cp1252")
    assert b"Caf\xe9 Cr\xe8me" in cp.read_bytes()
