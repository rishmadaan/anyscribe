"""The JavaScript runtime yt-dlp needs for YouTube: detection, flags, warning."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import anyscribe.core.deps as deps


def _which(table: dict[str, str | None]):
    return lambda name: table.get(name)


def _versions(table: dict[str, tuple[int, str]]):
    """Fake `<path> --version`: table maps path -> (returncode, output)."""

    def run(cmd, **kwargs):
        rc, out = table.get(cmd[0], (127, ""))
        return MagicMock(returncode=rc, stdout=out, stderr="")

    return run


@pytest.fixture
def empty_home(tmp_path: Path):
    with patch.object(deps.Path, "home", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def fresh_warning(monkeypatch):
    monkeypatch.setattr(deps, "_js_runtime_warned", False)


def test_prefers_deno_on_path(empty_home) -> None:
    with (
        patch.object(
            deps.shutil, "which", _which({"deno": "/opt/bin/deno", "node": "/usr/bin/node"})
        ),
        patch.object(
            deps.subprocess,
            "run",
            _versions(
                {"/opt/bin/deno": (0, "deno 2.9.7 (stable)"), "/usr/bin/node": (0, "v26.9.0")}
            ),
        ),
    ):
        rt = deps.find_js_runtime()
    assert rt == ("deno", "/opt/bin/deno", "deno 2.9.7")
    assert deps.js_runtime_args(rt) == ["--js-runtimes", "deno:/opt/bin/deno"]


def test_falls_back_to_node_with_explicit_flag(empty_home) -> None:
    with (
        patch.object(deps.shutil, "which", _which({"node": "/usr/bin/node"})),
        patch.object(deps.subprocess, "run", _versions({"/usr/bin/node": (0, "v24.22.0")})),
    ):
        rt = deps.find_js_runtime()
    assert rt == ("node", "/usr/bin/node", "node 24.22.0")
    assert deps.js_runtime_args(rt) == ["--js-runtimes", "node:/usr/bin/node"]


def test_skips_old_deno_and_old_node_and_impostors(empty_home) -> None:
    table = {
        "/old/deno": (0, "deno 2.2.0 (stable)"),
        "/usr/bin/node": (0, "v18.20.0"),
    }
    with (
        patch.object(deps.shutil, "which", _which({"deno": "/old/deno", "node": "/usr/bin/node"})),
        patch.object(deps.subprocess, "run", _versions(table)),
    ):
        assert deps.find_js_runtime() is None
    table = {"/fake/deno": (0, "something else 9.9.9"), "/usr/bin/node": (0, "v22.0.0")}
    with (
        patch.object(deps.shutil, "which", _which({"deno": "/fake/deno", "node": "/usr/bin/node"})),
        patch.object(deps.subprocess, "run", _versions(table)),
    ):
        assert deps.find_js_runtime() == ("node", "/usr/bin/node", "node 22.0.0")


def test_finds_deno_installed_by_its_script_off_path(empty_home) -> None:
    deno = empty_home / ".deno" / "bin" / "deno"
    deno.parent.mkdir(parents=True)
    deno.write_text("#!/bin/sh\n")
    deno.chmod(0o755)
    with (
        patch.object(deps.shutil, "which", _which({})),
        patch.object(deps.subprocess, "run", _versions({str(deno): (0, "deno 2.3.0 (stable)")})),
    ):
        assert deps.find_js_runtime() == ("deno", str(deno), "deno 2.3.0")


def test_no_runtime_gives_no_flags_and_warns_once(empty_home, fresh_warning, capsys) -> None:
    with patch.object(deps.shutil, "which", _which({})):
        rt = deps.find_js_runtime()
    assert rt is None
    assert deps.js_runtime_args(rt) == []
    deps.warn_if_no_js_runtime(rt)
    deps.warn_if_no_js_runtime(rt)
    captured = capsys.readouterr()
    assert captured.out == ""  # stdout stays clean for --json callers
    err = " ".join(captured.err.split())  # rich wraps at 80 columns
    assert err.count("No JavaScript runtime found") == 1
    assert "anyscribe doctor" in err


def test_youtube_command_carries_runtime_flag(tmp_path: Path) -> None:
    from anyscribe.downloaders.youtube import YouTubeDownloader

    (tmp_path / "x.mp3").write_bytes(b"x")
    run = MagicMock(
        side_effect=[
            MagicMock(returncode=0, stdout='{"title": "t"}', stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
    )
    with (
        patch("anyscribe.downloaders.youtube.subprocess.run", run),
        patch("anyscribe.core.deps.ensure_ytdlp_current"),
        patch(
            "anyscribe.core.deps.find_js_runtime",
            return_value=("node", "/usr/bin/node", "node 24.0.0"),
        ),
    ):
        YouTubeDownloader().download("https://youtu.be/abc", tmp_path)
    assert len(run.call_args_list) == 2
    for call in run.call_args_list:
        cmd = call.args[0]
        assert cmd[cmd.index("--js-runtimes") + 1] == "node:/usr/bin/node"


def test_doctor_row_names_the_runtime() -> None:
    with patch.object(
        deps, "find_js_runtime", return_value=("node", "/usr/bin/node", "node 26.9.0")
    ):
        row = next(r for r in deps.check_dependencies() if r.dep.name == "JavaScript runtime")
    assert row.found is True
    assert row.version == "node 26.9.0"
    assert row.path == "/usr/bin/node"


def test_ytdlp_auto_update_keeps_the_default_extra() -> None:
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        if "--version" in cmd:
            return MagicMock(returncode=0, stdout="2020.01.01", stderr="")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch.object(deps.subprocess, "run", run):
        deps.ensure_ytdlp_current()
    upgrade = next(c for c in calls if "install" in c)
    assert upgrade[-1] == "yt-dlp[default]"


def test_node_impostors_and_warning_lines_are_not_versions(empty_home) -> None:
    cases = {
        "/usr/bin/node": (0, "unrelated-tool 99.1.2"),
    }
    with (
        patch.object(deps.shutil, "which", _which({"node": "/usr/bin/node"})),
        patch.object(deps.subprocess, "run", _versions(cases)),
    ):
        assert deps.find_js_runtime() is None
    cases = {"/usr/bin/node": (0, "warning: build 2026.10.22\nv18.20.0")}
    with (
        patch.object(deps.shutil, "which", _which({"node": "/usr/bin/node"})),
        patch.object(deps.subprocess, "run", _versions(cases)),
    ):
        assert deps.find_js_runtime() is None  # 18 is too old; the date is not a version
    cases = {"/usr/bin/node": (0, "warning: helper 1.2.3\nv24.22.0")}
    with (
        patch.object(deps.shutil, "which", _which({"node": "/usr/bin/node"})),
        patch.object(deps.subprocess, "run", _versions(cases)),
    ):
        assert deps.find_js_runtime() == ("node", "/usr/bin/node", "node 24.22.0")


def test_failed_probe_is_skipped(empty_home) -> None:
    cases = {"/usr/bin/node": (1, "v24.22.0")}
    with (
        patch.object(deps.shutil, "which", _which({"node": "/usr/bin/node"})),
        patch.object(deps.subprocess, "run", _versions(cases)),
    ):
        assert deps.find_js_runtime() is None
