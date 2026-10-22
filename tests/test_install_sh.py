"""Static guards for install.sh — the bugs these catch shipped once already."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "install.sh"
SRC = SCRIPT.read_text()


def test_bash_syntax_ok():
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    subprocess.run([bash, "-n", str(SCRIPT)], check=True)


def test_brew_activated_in_current_shell_after_install():
    # Fresh Homebrew installs are not on PATH in the running script;
    # without this eval the very next brew call dies on Apple Silicon.
    assert 'eval "$(/opt/homebrew/bin/brew shellenv)"' in SRC


def test_no_bare_pip3_installs():
    # Modern macOS blocks the stock pip3 (externally-managed). Every install
    # must go through the resolved "$PY" -m pip.
    assert "pip3 install" not in SRC


def test_tray_extra_is_installed_on_pip_path():
    assert "anyscribe[tray]" in SRC


def test_homebrew_prompt_warns_about_password_and_time():
    assert "password" in SRC and "10-20 minutes" in SRC


def test_skipped_pipx_launch_does_not_claim_ready(tmp_path):
    # --ui with pipx but no anyscribe executable: must not print the "ready" banner.
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    assert SRC.rstrip().splitlines()[-1] == "main"
    harness = (
        'eval "$(sed \'$d\' "$SCRIPT")"\n'  # load everything except the final `main` call
        "install_brew_if_needed(){ :; }; check_python(){ :; }; check_ytdlp(){ :; }\n"
        "check_ffmpeg(){ :; }; check_js_runtime(){ :; }; install_anyscribe(){ USED_PIPX=true; }\n"
        'command_exists(){ return 1; }; pipx(){ echo "$BIN"; }\n'
        "RUN_UI=true\nmain\n"
    )
    out = subprocess.run(
        [bash, "-c", harness],
        env={**os.environ, "SCRIPT": str(SCRIPT), "BIN": str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "Automatic launch skipped" in out
    assert "anyscribe is ready!" not in out


def _run_js_runtime_step(tmp_path, node_version, answer):
    """Run check_js_runtime under a pseudo-terminal (the prompt reads /dev/tty)
    with a fake node and fake brew/curl that only record their calls."""
    bash = shutil.which("bash")
    script = shutil.which("script")
    if not bash or not script:
        pytest.skip("bash and script(1) needed")
    calls = tmp_path / "calls"
    harness = tmp_path / "harness.sh"
    harness.write_text(
        # macOS script(1) exports its own SCRIPT variable, hence INSTALL_SH here.
        'eval "$(sed \'$d\' "$INSTALL_SH")"\n'
        'ok(){ echo "ok: $*"; }; warn(){ echo "warn: $*"; }; info(){ :; }\n'
        "command(){ return 1; }\n"  # hides the test machine's real deno from `command -v`
        'command_exists(){ [[ "$1" == node || "$1" == brew ]]; }\n'
        'node(){ echo "$NODE_VERSION"; }\n'
        'brew(){ echo "brew $*" >> "$CALLS"; }; curl(){ echo "curl $*" >> "$CALLS"; }\n'
        "OS=macos; HOME=/nonexistent\n"
        'check_js_runtime; echo "step exit=$?"\n'
    )
    pty = (
        f'"{script}" -q /dev/null "{bash}" "{harness}"'
        if os.uname().sysname == "Darwin"
        else f'"{script}" -qec "{bash} {harness}" /dev/null'
    )
    # The answer is fed after a pause and the pipe is held open afterwards: an
    # EOF on the pty that arrives with or before the answer makes the prompt's
    # read fail, and the step takes its "no terminal" exit instead.
    out = subprocess.run(
        [bash, "-c", f'(sleep 1; printf "%s\\n" "$ANSWER"; sleep 4) | {pty}'],
        env={
            **os.environ,
            "INSTALL_SH": str(SCRIPT),
            "NODE_VERSION": node_version,
            "CALLS": str(calls),
            "ANSWER": answer,
        },
        capture_output=True,
        text=True,
        timeout=60,
    )
    return out.stdout + out.stderr, calls.read_text() if calls.exists() else ""


def test_node_22_means_no_deno_install(tmp_path):
    out, calls = _run_js_runtime_step(tmp_path, "v24.22.0", "")
    assert "ok: node v24.22.0" in out
    assert "step exit=0" in out
    assert calls == ""


def test_old_node_prompts_and_decline_only_warns(tmp_path):
    out, calls = _run_js_runtime_step(tmp_path, "v18.19.1", "n")
    assert "needs 22 or newer" in out
    assert "Skipping. Install Deno later" in out  # the decline branch, not the no-terminal one
    assert "step exit=0" in out
    assert calls == ""


def test_old_node_accept_installs_deno(tmp_path):
    out, calls = _run_js_runtime_step(tmp_path, "v18.19.1", "y")
    assert "brew install deno" in calls
    assert "step exit=0" in out


def test_node_that_fails_its_probe_is_not_accepted(tmp_path):
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    harness = (
        'eval "$(sed \'$d\' "$INSTALL_SH")"\n'
        'ok(){ echo "ok: $*"; }; warn(){ echo "warn: $*"; }\n'
        'command(){ return 1; }; command_exists(){ [[ "$1" == node ]]; }\n'
        "node(){ echo v24.22.0; return 1; }\n"  # a banner that looks right, from a failing program
        "HOME=/nonexistent\n"
        'js_runtime_found && echo accepted || echo "not accepted"\n'
    )
    out = subprocess.run(
        [bash, "-c", harness],
        env={**os.environ, "INSTALL_SH": str(SCRIPT)},
        capture_output=True,
        text=True,
    ).stdout
    assert "not accepted" in out
    assert "accepted\n" not in out.replace("not accepted\n", "")


def test_check_python_asks_each_package_manager_by_its_own_names(tmp_path):
    bash = shutil.which("bash")
    script = shutil.which("script")
    if not bash or not script:
        pytest.skip("bash and script(1) needed")
    results = {}
    for mgr in ("apt", "pacman", "dnf"):
        calls = tmp_path / f"calls-{mgr}"
        harness = tmp_path / f"harness-{mgr}.sh"
        harness.write_text(
            'eval "$(sed \'$d\' "$INSTALL_SH")"\n'
            'ok(){ :; }; warn(){ :; }; info(){ :; }; die(){ echo "die: $1"; }\n'
            "resolve_python(){ return 1; }\n"
            'install_package(){ echo "$3" >> "$CALLS"; }\n'
            f"LINUX_PKG={mgr}; OS=linux\n"
            "check_python\n"
        )
        pty = (
            f'"{script}" -q /dev/null "{bash}" "{harness}"'
            if os.uname().sysname == "Darwin"
            else f'"{script}" -qec "{bash} {harness}" /dev/null'
        )
        subprocess.run(
            [bash, "-c", f'(sleep 1; printf "y\\n"; sleep 4) | {pty}'],
            env={**os.environ, "INSTALL_SH": str(SCRIPT), "CALLS": str(calls)},
            capture_output=True,
            text=True,
            timeout=60,
        )
        results[mgr] = calls.read_text().splitlines() if calls.exists() else []
    assert results["apt"] == ["python3 python3-venv", "python3.11 python3.11-venv"]
    assert results["dnf"] == ["python3", "python3.11"]
    assert results["pacman"] == ["python3"]


def _js_runtime_verdict(tmp_path, setup):
    """Run js_runtime_found with fake programs; returns the installer's output."""
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    harness = (
        'eval "$(sed \'$d\' "$INSTALL_SH")"\n'
        'ok(){ echo "ok: $*"; }; warn(){ echo "warn: $*"; }\n'
        'command(){ return 1; }; command_exists(){ [[ "$1" == node && -n "${HAVE_NODE:-}" ]]; }\n'
        f"HOME={tmp_path}\n" + setup + "\n"
        'js_runtime_found && echo "verdict: accepted" || echo "verdict: not accepted"\n'
    )
    return subprocess.run(
        [bash, "-c", harness],
        env={**os.environ, "INSTALL_SH": str(SCRIPT)},
        capture_output=True,
        text=True,
    ).stdout


@pytest.mark.parametrize(
    "setup,expected",
    [
        (
            'HAVE_NODE=1; node(){ echo "npm warn x"; echo v24.22.0; }',
            "accepted",
        ),  # warning before the banner
        ("HAVE_NODE=1; node(){ echo v24.22.0 >&2; }", "accepted"),  # banner on stderr
        ('HAVE_NODE=1; node(){ echo "unrelated-tool 99.1.2"; }', "not accepted"),  # impostor
        ("HAVE_NODE=1; node(){ echo v18.20.0; }", "not accepted"),  # too old
    ],
)
def test_node_banner_cases(tmp_path, setup, expected):
    out = _js_runtime_verdict(tmp_path, setup)
    assert f"verdict: {expected}" in out


@pytest.mark.parametrize(
    "banner,expected",
    [
        ("deno 2.3.", "not accepted"),  # a truncated banner is not a version
        ("deno 2.3.0 (stable)\r", "accepted"),  # CRLF output
        ("deno 2.2.9 (stable)", "not accepted"),  # below yt-dlp's minimum
        ("something-else 2.9.0", "not accepted"),  # a same-named unrelated program
        (
            "deno 2.3.0rc1 (stable)",
            "not accepted",
        ),  # malformed suffix glued to the patch, as Python treats it
        ("deno 2.3.0-rc.1 (stable)", "accepted"),  # a real release candidate banner
    ],
)
def test_home_deno_banner_cases(tmp_path, banner, expected):
    deno = tmp_path / ".deno" / "bin" / "deno"
    deno.parent.mkdir(parents=True)
    deno.write_text("#!/bin/sh\nprintf '%s\\n' " + repr(banner).replace("\\r", "\\r") + "\n")
    deno.chmod(0o755)
    out = _js_runtime_verdict(tmp_path, "")
    assert f"verdict: {expected}" in out


def run_installer_dry(tmp_path, *args, dry_run=True, setup=""):
    """Run install.sh's main with the dependency checks stubbed out; returns stdout+stderr."""
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    harness = (
        'eval "$(sed \'$d\' "$SCRIPT")"\n'  # load everything except the final `main` call
        "install_brew_if_needed(){ :; }; check_python(){ :; }; check_ytdlp(){ :; }\n"
        "check_ffmpeg(){ :; }; check_js_runtime(){ :; }\n" + setup + "\nmain\n"
    )
    flags = (["--dry-run"] if dry_run else []) + list(args)
    out = subprocess.run(
        [bash, "-c", harness, "install.sh", *flags],
        env={**os.environ, "SCRIPT": str(SCRIPT)},
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout + out.stderr


def test_dry_run_installs_desktop_by_default(tmp_path):
    out = run_installer_dry(tmp_path)
    assert "desktop install --yes" in out


def test_no_desktop_flag_skips_it(tmp_path):
    out = run_installer_dry(tmp_path, "--no-desktop")
    assert "desktop install" not in out and "anyscribe ui" in out


def test_git_method_skips_desktop_and_says_why(tmp_path):
    out = run_installer_dry(tmp_path, "--method", "git")
    # The skip notice names the retry command, so check that nothing ran it.
    assert "[dry-run]" in out and "desktop install --yes" not in out
    assert "Desktop mode skipped" in out and "[tray]" in out


def test_ps1_has_nodesktop_switch_and_desktop_step():
    txt = (SCRIPT.parent / "install.ps1").read_text()
    assert "[switch]$NoDesktop" in txt and "desktop install --yes" in txt


def test_failed_desktop_install_does_not_claim_desktop_mode(tmp_path):
    # A real (not dry) run where everything succeeds except `desktop install`.
    setup = (
        "install_anyscribe(){ :; }\n"
        'python3(){ [[ "$*" == *"desktop install"* ]] && { echo "desktop boom"; return 1; }; return 0; }\n'
    )
    out = run_installer_dry(tmp_path, dry_run=False, setup=setup)
    assert "desktop boom" in out  # its own output is shown
    assert "Desktop mode was not set up (see above)" in out
    assert "running in your" not in out  # no desktop-mode claim
    assert "Next step:" in out and "anyscribe ui" in out


def test_ui_flag_does_not_launch_ui_when_desktop_runs(tmp_path):
    out = run_installer_dry(tmp_path, "--ui")
    assert "desktop install --yes" in out
    assert not [ln for ln in out.splitlines() if "[dry-run]" in ln and ln.rstrip().endswith(" ui")]


def test_onboard_runs_before_desktop(tmp_path):
    lines = run_installer_dry(tmp_path, "--onboard").splitlines()
    onboard = next(
        i for i, ln in enumerate(lines) if "[dry-run]" in ln and "onboard --skip-deps" in ln
    )
    desktop = next(
        i for i, ln in enumerate(lines) if "[dry-run]" in ln and "desktop install --yes" in ln
    )
    assert onboard < desktop


def test_pipx_hint_shows_after_default_desktop_run(tmp_path):
    # The pipx PATH hint must not depend on which banner printed.
    exe = tmp_path / "anyscribe"
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)
    setup = f'install_anyscribe(){{ USED_PIPX=true; }}; pipx(){{ echo "{tmp_path}"; }}\n'
    out = run_installer_dry(tmp_path, setup=setup)
    assert "[dry-run]" in out and "desktop install --yes" in out
    assert "anyscribe is ready!" in out
    assert "pipx ensurepath" in out
