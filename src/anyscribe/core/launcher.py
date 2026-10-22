"""App icon + per-OS launcher that opens the dashboard.

macOS: ``~/Applications/anyscribe.app``; Windows: a Start-menu ``.lnk``;
Linux: an XDG ``.desktop`` entry. Each runs
``<python> -m anyscribe desktop open --port <port>``.

Pillow imports are lazy: the base install has no Pillow.
"""

from __future__ import annotations

import io
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from importlib.resources import files
from pathlib import Path
from xml.sax.saxutils import escape

APP_NAME = "anyscribe"
ICO_SIZES = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]
ICONSET_SIZES = (16, 32, 128, 256, 512)


def _open_command(python: str, port: int) -> str:
    return f"{shlex.quote(python)} -m anyscribe desktop open --port {port}"


# ---- pure renderers ------------------------------------------------------


def render_app_script(python: str, port: int) -> str:
    return f"#!/bin/sh\nexec {_open_command(python, port)}\n"


def render_info_plist(icon_file: str = APP_NAME) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>{APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>com.anyscribe.app</string>
    <key>CFBundleExecutable</key>
    <string>{APP_NAME}</string>
    <key>CFBundleIconFile</key>
    <string>{escape(icon_file)}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
"""


_DESKTOP_RESERVED = set(" \t\n\"'\\><~|&;$*?#()`")
# The string-value escape layer is decoded BEFORE the quoting layer, so each
# backslash the quoting produces must itself be doubled (spec: a literal "\"
# in a quoted argument is four backslashes, a literal "$" is "\\$").
_DESKTOP_STRING_ESCAPES = str.maketrans({"\\": "\\\\", "\n": "\\n", "\t": "\\t", "\r": "\\r"})


def desktop_quote(arg: str) -> str:
    """Quote one argument for a Desktop Entry ``Exec`` value (freedesktop spec)."""
    if any(c in _DESKTOP_RESERVED for c in arg):
        quoted = "".join("\\" + c if c in '\\"`$' else c for c in arg)
        arg = f'"{quoted}"'.translate(_DESKTOP_STRING_ESCAPES)
    return arg.replace("%", "%%")


def render_desktop_entry(python: str, port: int, icon: str = APP_NAME) -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f"Exec={desktop_quote(python)} -m anyscribe desktop open --port {port}\n"
        f"Icon={icon}\n"
        "Terminal=false\n"
        "Categories=AudioVideo;Utility;\n"
    )


def _ps_quote(value: object) -> str:
    """PowerShell single-quoted literal: no expansion; a ' is written ''."""
    return "'" + str(value).replace("'", "''") + "'"


def render_shortcut_script(
    lnk: Path, target: str, arguments: str, icon: Path | None, description: str
) -> str:
    lines = [
        f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut({_ps_quote(lnk)})",
        f"$s.TargetPath = {_ps_quote(target)}",
        f"$s.Arguments = {_ps_quote(arguments)}",
        f"$s.Description = {_ps_quote(description)}",
    ]
    if icon is not None:
        lines.append(f"$s.IconLocation = {_ps_quote(icon)}")
    lines.append("$s.Save()")
    return "; ".join(lines)


# ---- locations (module-level so tests can monkeypatch them) --------------


def applications_dir() -> Path:
    return Path.home() / "Applications"


def start_menu_dir() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def xdg_applications_dir() -> Path:
    return Path.home() / ".local" / "share" / "applications"


def xdg_icon_path() -> Path:
    return (
        Path.home()
        / ".local"
        / "share"
        / "icons"
        / "hicolor"
        / "512x512"
        / "apps"
        / "anyscribe.png"
    )


def launcher_path() -> Path:
    if sys.platform == "darwin":
        return applications_dir() / f"{APP_NAME}.app"
    if sys.platform == "win32":
        return start_menu_dir() / f"{APP_NAME}.lnk"
    return xdg_applications_dir() / f"{APP_NAME}.desktop"


# ---- effects -------------------------------------------------------------


def pythonw(python: str | None = None) -> str:
    """The windowless interpreter on Windows, so the shortcut opens no console."""
    python = python or sys.executable
    if sys.platform == "win32":
        candidate = Path(python).with_name("pythonw.exe")
        if candidate.exists():
            return str(candidate)
    return python


def create_shortcut(
    lnk: Path, target: str, arguments: str, icon: Path | None, description: str
) -> None:
    lnk.parent.mkdir(parents=True, exist_ok=True)
    script = render_shortcut_script(lnk, target, arguments, icon, description)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Could not create shortcut {lnk}: {result.stderr.strip()}")


def render_icons(dest_dir: Path) -> dict[str, Path]:
    """Write the bundled icon as png (512), ico and, where iconutil exists, icns."""
    from PIL import Image

    data = files("anyscribe").joinpath("assets/app-icon.png").read_bytes()
    src = Image.open(io.BytesIO(data)).convert("RGBA")
    dest_dir.mkdir(parents=True, exist_ok=True)

    out = {"png": dest_dir / f"{APP_NAME}.png", "ico": dest_dir / f"{APP_NAME}.ico"}
    src.resize((512, 512), Image.LANCZOS).save(out["png"])
    src.save(out["ico"], sizes=ICO_SIZES)

    iconutil = shutil.which("iconutil")
    if iconutil:
        icns = dest_dir / f"{APP_NAME}.icns"
        with tempfile.TemporaryDirectory() as tmp:
            iconset = Path(tmp) / f"{APP_NAME}.iconset"
            iconset.mkdir()
            for size in ICONSET_SIZES:
                for scale, suffix in ((1, ""), (2, "@2x")):
                    px = size * scale
                    img = src.resize((px, px), Image.LANCZOS)
                    img.save(iconset / f"icon_{size}x{size}{suffix}.png")
            subprocess.run([iconutil, "-c", "icns", str(iconset), "-o", str(icns)], check=True)
        out["icns"] = icns
    return out


def install_launcher(python: str, port: int, icons: dict[str, Path]) -> Path:
    """Write the launcher for this OS. Returns its path."""
    path = launcher_path()
    if sys.platform == "darwin":
        if path.exists():
            shutil.rmtree(path)  # no stale files from an older bundle
        contents = path / "Contents"
        script = contents / "MacOS" / APP_NAME
        script.parent.mkdir(parents=True)
        script.write_text(render_app_script(python, port))
        script.chmod(0o755)
        (contents / "Info.plist").write_text(render_info_plist())
        icns = icons.get("icns")
        if icns and icns.exists():
            (contents / "Resources").mkdir()
            shutil.copyfile(icns, contents / "Resources" / f"{APP_NAME}.icns")
        os.utime(path)  # Finder/Dock re-read the icon only when the bundle mtime moves
    elif sys.platform == "win32":
        create_shortcut(
            path,
            pythonw(python),
            f"-m anyscribe desktop open --port {port}",
            icons.get("ico"),
            APP_NAME,
        )
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_desktop_entry(python, port))
        png = icons.get("png")
        if png and png.exists():
            xdg_icon_path().parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(png, xdg_icon_path())
        udd = shutil.which("update-desktop-database")
        if udd:
            try:
                subprocess.run([udd, str(path.parent)], check=False)
            except OSError:
                pass  # the menu refreshes on its own later; not worth failing install
    return path


def uninstall_launcher() -> bool:
    """Remove the launcher (and the Linux icon copy). True if it existed."""
    path = launcher_path()
    existed = path.exists()
    if path.is_dir():
        shutil.rmtree(path)
    elif existed:
        path.unlink()
    if sys.platform not in ("darwin", "win32"):
        xdg_icon_path().unlink(missing_ok=True)
    return existed
