"""Launcher + icon tests. Nothing is installed for real: every location is under tmp_path."""

from __future__ import annotations

import os
import re
import shlex
import sys
from pathlib import Path

import pytest

from anyscribe.core import launcher


@pytest.fixture
def home(tmp_path, monkeypatch):
    # A space and an apostrophe: both break naive shell / PowerShell quoting.
    h = tmp_path / "Rish O'Brien"
    h.mkdir()
    monkeypatch.setattr(Path, "home", lambda: h)
    return h


def test_renders_quote_paths_with_space_and_apostrophe(home):
    py = str(home / "py env" / "python3")
    assert shlex.quote(py) in launcher.render_app_script(py, 8457)
    # A .desktop file is a Linux artifact: its path never has backslashes (which desktop_quote doubles).
    py_posix = "/home/Rish O'Brien/py env/python3"
    entry = launcher.render_desktop_entry(py_posix, 8457)
    assert f'Exec="{py_posix}" -m anyscribe' in entry and "\\'" not in entry
    ps = launcher.render_shortcut_script(home / "a.lnk", py, "-m anyscribe tray", None, "anyscribe")
    assert "Rish O''Brien" in ps and "$s.Save()" in ps


def test_ps_quote_doubles_curly_apostrophes():
    ps = launcher.render_shortcut_script(Path("C:/Rish O\u2019Brien/a.lnk"), "py", "", None, "x")
    assert "Rish O\u2019\u2019Brien" in ps
    assert launcher._ps_quote("\u2018\u201a\u201b") == "'\u2018\u2018\u201a\u201a\u201b\u201b'"


def test_app_script_execs_desktop_open():
    assert launcher.render_app_script("/usr/bin/python3", 8457) == (
        "#!/bin/sh\nexec /usr/bin/python3 -m anyscribe desktop open --port 8457\n"
    )


def _desktop_unquote(value: str) -> str:
    """Reference decoder for one Exec argument: string escapes, then quoting, then %%."""
    unescaped = re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t", "r": "\r"}.get(m[1], m[1]), value)
    if unescaped.startswith('"'):
        unescaped = re.sub(r"\\(.)", r"\1", unescaped[1:-1])
    return unescaped.replace("%%", "%")


def test_desktop_quote_escapes_reserved_and_percent():
    raw = '/a b/$x"y\\z%'
    assert launcher.desktop_quote(raw) == '"/a b/\\\\$x\\\\"y\\\\\\\\z%%"'
    assert _desktop_unquote(launcher.desktop_quote(raw)) == raw
    assert launcher.desktop_quote("/usr/bin/python3") == "/usr/bin/python3"
    assert launcher.desktop_quote("/opt/100%/python") == "/opt/100%%/python"


def test_info_plist_is_background_launcher():
    xml = launcher.render_info_plist()
    assert "<key>LSUIElement</key>" in xml and "<string>com.anyscribe.app</string>" in xml


def test_desktop_entry_fields():
    txt = launcher.render_desktop_entry("/usr/bin/python3", 8457)
    assert "Terminal=false" in txt and "Icon=anyscribe" in txt and "--port 8457" in txt
    # One main category plus an additional one, or some menus list the app twice.
    assert "\nCategories=AudioVideo;Audio;\n" in txt


def test_install_launcher_macos_writes_app_tree(home, monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher, "applications_dir", lambda: home / "Applications")
    app = launcher.install_launcher("/usr/bin/python3", 8457, {"icns": home / "i.icns"})
    if os.name != "nt":  # no executable bit on Windows
        assert (app / "Contents" / "MacOS" / "anyscribe").stat().st_mode & 0o111
    assert (app / "Contents" / "Info.plist").exists()
    assert app.stat().st_mtime_ns >= (app / "Contents" / "MacOS" / "anyscribe").stat().st_mtime_ns
    assert launcher.uninstall_launcher() is True and not app.exists()


def test_install_launcher_macos_copies_icns(home, monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher, "applications_dir", lambda: home / "Applications")
    icns = home / "i.icns"
    icns.write_bytes(b"icns-bytes")
    app = launcher.install_launcher("/usr/bin/python3", 8457, {"icns": icns})
    assert (app / "Contents" / "Resources" / "anyscribe.icns").read_bytes() == b"icns-bytes"


def test_install_launcher_linux_writes_desktop_and_icon(home, monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    png = home / "src.png"
    png.write_bytes(b"png-bytes")
    calls = []
    monkeypatch.setattr(launcher.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(launcher.subprocess, "run", lambda cmd, **kw: calls.append(cmd))

    entry = launcher.install_launcher("/usr/bin/python3", 8457, {"png": png})

    apps = home / ".local" / "share" / "applications"
    assert entry == apps / "anyscribe.desktop"
    assert "Exec=/usr/bin/python3 -m anyscribe desktop open --port 8457" in entry.read_text()
    assert launcher.xdg_icon_path().read_bytes() == b"png-bytes"
    assert calls == [["/usr/bin/update-desktop-database", str(apps)]]
    assert launcher.uninstall_launcher() is True and not entry.exists()


def test_install_launcher_windows_calls_create_shortcut(home, monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "win32")
    # A fake interpreter that is not sys.executable: the target must come from it.
    python = home / "py env" / "python.exe"
    python.parent.mkdir()
    python.write_text("")
    (python.parent / "pythonw.exe").write_text("")
    monkeypatch.setattr(launcher, "start_menu_dir", lambda: home / "Programs")
    seen = {}
    monkeypatch.setattr(launcher, "create_shortcut", lambda *a: seen.update(args=a))
    (home / "a.ico").write_bytes(b"ico")

    lnk = launcher.install_launcher(str(python), 8457, {"ico": home / "a.ico"})

    assert lnk == home / "Programs" / "anyscribe.lnk"
    assert seen["args"] == (
        lnk,
        str(python.parent / "pythonw.exe"),
        "-m anyscribe desktop open --port 8457",
        home / "a.ico",
        "anyscribe",
    )


def test_install_launcher_windows_skips_missing_icon(home, monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "win32")
    monkeypatch.setattr(launcher, "start_menu_dir", lambda: home / "Programs")
    seen = {}
    monkeypatch.setattr(launcher, "create_shortcut", lambda *a: seen.update(args=a))
    launcher.install_launcher("python", 8457, {"ico": home / "missing.ico"})
    assert seen["args"][3] is None


def test_create_shortcut_passes_timeout_and_wraps_missing_powershell(tmp_path, monkeypatch):
    seen = {}

    def run(*a, **kw):
        seen.update(kw)
        raise FileNotFoundError("powershell")

    monkeypatch.setattr(launcher.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="powershell"):
        launcher.create_shortcut(tmp_path / "a.lnk", "python", "", None, "x")
    assert seen["timeout"] == 60


def test_create_shortcut_raises_on_failure(tmp_path, monkeypatch):
    class Failed:
        returncode = 1
        stderr = "boom"
        stdout = ""

    monkeypatch.setattr(launcher.subprocess, "run", lambda *a, **kw: Failed())
    with pytest.raises(RuntimeError, match="boom"):
        launcher.create_shortcut(tmp_path / "a.lnk", "python", "", None, "x")


def test_uninstall_launcher_absent_returns_false(home, monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher, "applications_dir", lambda: home / "Applications")
    assert launcher.uninstall_launcher() is False


@pytest.mark.skipif(sys.platform != "darwin", reason="iconutil")
def test_render_icons_real_icns(tmp_path):
    out = launcher.render_icons(tmp_path)
    assert out["icns"].stat().st_size > 1000


@pytest.mark.skipif(sys.platform != "win32", reason="WScript.Shell")
def test_create_shortcut_real_lnk(tmp_path):
    lnk = tmp_path / "anyscribe.lnk"
    launcher.create_shortcut(lnk, sys.executable, "-m anyscribe --version", None, "test")
    assert lnk.exists()


def test_render_icons_png_and_ico(tmp_path):
    pytest.importorskip("PIL")
    out = launcher.render_icons(tmp_path)
    assert out["png"].exists() and out["ico"].exists()
