"""The JavaScript runtime yt-dlp needs for YouTube: detection, flags, warning."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import anyscribe.core.deps as deps


def _which(table: dict[str, str | None]):
    return lambda name: table.get(name)


def test_prefers_deno_on_path(tmp_path: Path) -> None:
    with patch.object(
        deps.shutil, "which", _which({"deno": "/opt/bin/deno", "node": "/usr/bin/node"})
    ):
        assert deps.find_js_runtime() == ("deno", "/opt/bin/deno")
        assert deps.js_runtime_args() == ["--js-runtimes", "deno:/opt/bin/deno"]


def test_falls_back_to_node_with_explicit_flag() -> None:
    with patch.object(deps.shutil, "which", _which({"node": "/usr/bin/node"})):
        assert deps.find_js_runtime() == ("node", "/usr/bin/node")
        assert deps.js_runtime_args() == ["--js-runtimes", "node:/usr/bin/node"]


def test_finds_deno_installed_by_its_script_off_path(tmp_path: Path) -> None:
    deno = tmp_path / ".deno" / "bin" / "deno"
    deno.parent.mkdir(parents=True)
    deno.write_text("#!/bin/sh\n")
    deno.chmod(0o755)
    with (
        patch.object(deps.shutil, "which", _which({})),
        patch.object(deps.Path, "home", return_value=tmp_path),
    ):
        assert deps.find_js_runtime() == ("deno", str(deno))


def test_no_runtime_gives_no_flags_and_warns_once(capsys) -> None:
    deps._js_runtime_warned = False
    with (
        patch.object(deps.shutil, "which", _which({})),
        patch.object(deps.Path, "home", return_value=Path("/nonexistent")),
    ):
        assert deps.js_runtime_args() == []
        deps.warn_if_no_js_runtime()
        deps.warn_if_no_js_runtime()
    out = capsys.readouterr().out
    assert out.count("No JavaScript runtime found") == 1
    assert "anyscribe doctor" in out


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
        patch("anyscribe.core.deps.find_js_runtime", return_value=("node", "/usr/bin/node")),
    ):
        YouTubeDownloader().download("https://youtu.be/abc", tmp_path)
    for call in run.call_args_list:
        cmd = call.args[0]
        assert cmd[cmd.index("--js-runtimes") + 1] == "node:/usr/bin/node"


def test_doctor_row_names_the_runtime() -> None:
    with (
        patch.object(deps, "find_js_runtime", return_value=("node", "/usr/bin/node")),
        patch.object(deps, "_get_version", return_value="v26.9.0"),
    ):
        row = next(r for r in deps.check_dependencies() if r.dep.name == "JavaScript runtime")
    assert row.found is True
    assert row.version == "node v26.9.0"
    assert row.path == "/usr/bin/node"
