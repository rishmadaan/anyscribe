#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# anyscribe installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.sh | bash
#
# Or with options:
#   curl -fsSL ... | bash -s -- --method git --ui
#
# What it does:
#   1. Checks your OS (macOS or Linux)
#   2. Checks for Python 3.11+, installs if missing
#   3. Checks for yt-dlp, ffmpeg and a JavaScript runtime (Deno or Node 22+), installs if missing
#   4. Installs anyscribe (with the tray extra) via pip (with pipx fallback)
#   5. Tells you to run `anyscribe ui`
# ──────────────────────────────────────────────────────────────

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────
INSTALL_METHOD="pip"       # pip (from PyPI) or git (from GitHub)
REPO_URL="https://github.com/rishmadaan/anyscribe.git"
RUN_ONBOARD=false
RUN_UI=false
VERBOSE=false
DRY_RUN=false
USED_PIPX=false
POST_INSTALL_SKIPPED=false
PY="python3"

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Helpers ───────────────────────────────────────────────────
info()  { echo -e "${BLUE}${BOLD}==>${NC} $1"; }
ok()    { echo -e "${GREEN}${BOLD}  ✓${NC} $1"; }
warn()  { echo -e "${YELLOW}${BOLD}  !${NC} $1"; }
fail()  { echo -e "${RED}${BOLD}  ✗${NC} $1"; }
die()   { fail "$1"; exit 1; }

command_exists() { command -v "$1" &>/dev/null; }

# Find a Python >= 3.11, preferring version-suffixed binaries (a brew
# python@3.12 install provides python3.12; the bare python3 may still be
# the old system one).
resolve_python() {
    local cand
    for cand in python3.14 python3.13 python3.12 python3.11 python3; do
        if command_exists "$cand" && "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
            PY="$cand"
            return 0
        fi
    done
    return 1
}

# ── Parse arguments ───────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --method)       INSTALL_METHOD="$2"; shift 2 ;;
        --repo)         REPO_URL="$2"; shift 2 ;;
        --onboard)      RUN_ONBOARD=true; shift ;;
        --ui)           RUN_UI=true; shift ;;
        --verbose)      VERBOSE=true; shift ;;
        --dry-run)      DRY_RUN=true; shift ;;
        --help|-h)
            echo "anyscribe installer"
            echo ""
            echo "Usage: curl -fsSL <url>/install.sh | bash -s -- [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --method <pip|git>   Install method (default: pip)"
            echo "                       pip: install from PyPI (default)"
            echo "                       git: install from GitHub repository"
            echo "  --repo <url>         GitHub repo URL (for git method)"
            echo "  --onboard            Run the CLI onboarding wizard after install"
            echo "  --ui                 Launch the web UI after install"
            echo "  --verbose            Show detailed output"
            echo "  --dry-run            Show what would be done without doing it"
            echo "  --help               Show this help"
            exit 0
            ;;
        *) die "Unknown option: $1 (use --help for usage)" ;;
    esac
done

# ── Detect OS ─────────────────────────────────────────────────
detect_os() {
    local os
    os="$(uname -s)"
    case "$os" in
        Darwin) echo "macos" ;;
        Linux)  echo "linux" ;;
        *)      die "Unsupported operating system: $os. anyscribe supports macOS and Linux." ;;
    esac
}

detect_linux_pkg_manager() {
    if command_exists apt; then echo "apt"
    elif command_exists dnf; then echo "dnf"
    elif command_exists pacman; then echo "pacman"
    else echo "unknown"; fi
}

OS="$(detect_os)"
LINUX_PKG=""
if [[ "$OS" == "linux" ]]; then
    LINUX_PKG="$(detect_linux_pkg_manager)"
fi

echo ""
echo -e "${BOLD}  ┌─────────────────────────────────────┐${NC}"
echo -e "${BOLD}  │       anyscribe installer           │${NC}"
echo -e "${BOLD}  │  Video → Transcript → Markdown      │${NC}"
echo -e "${BOLD}  └─────────────────────────────────────┘${NC}"
echo ""
info "Detected OS: $OS${LINUX_PKG:+ ($LINUX_PKG)}"

# ── Check / install Homebrew (macOS) ──────────────────────────
install_brew_if_needed() {
    if [[ "$OS" == "macos" ]] && ! command_exists brew; then
        warn "Homebrew not found. It's needed to install dependencies."
        echo "    Install from: https://brew.sh"
        read -rp "    Install Homebrew now? [Y/n] " answer </dev/tty
        answer="${answer:-Y}"
        if [[ "$answer" =~ ^[Yy] ]]; then
            info "Installing Homebrew..."
            warn "Homebrew will ask for your Mac password and can take 10-20 minutes — this is normal."
            if [[ "$DRY_RUN" == true ]]; then
                echo "    [dry-run] Would install Homebrew"
            else
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                # Fresh installs are not on PATH in this shell yet — activate now.
                if [[ -x /opt/homebrew/bin/brew ]]; then
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                elif [[ -x /usr/local/bin/brew ]]; then
                    eval "$(/usr/local/bin/brew shellenv)"
                fi
            fi
        else
            die "Cannot continue without a package manager. Install Homebrew from https://brew.sh and try again."
        fi
    fi
}

# ── Generic install helper ────────────────────────────────────
install_package() {
    local name="$1"
    local brew_pkg="$2"
    local apt_pkg="$3"
    local pip_pkg="${4:-}"

    if [[ "$OS" == "macos" ]]; then
        if command_exists brew; then
            info "Installing $name via Homebrew..."
            if [[ "$DRY_RUN" == true ]]; then
                echo "    [dry-run] brew install $brew_pkg"
            else
                brew install "$brew_pkg"
            fi
            return
        fi
    elif [[ "$OS" == "linux" ]]; then
        case "$LINUX_PKG" in
            apt)
                info "Installing $name via apt..."
                if [[ "$DRY_RUN" == true ]]; then
                    echo "    [dry-run] sudo apt install -y $apt_pkg"
                else
                    # shellcheck disable=SC2086  # apt_pkg may name several packages
                    sudo apt update -qq && sudo apt install -y $apt_pkg
                fi
                return
                ;;
            dnf)
                info "Installing $name via dnf..."
                if [[ "$DRY_RUN" == true ]]; then
                    echo "    [dry-run] sudo dnf install -y $apt_pkg"
                else
                    sudo dnf install -y "$apt_pkg"
                fi
                return
                ;;
            pacman)
                info "Installing $name via pacman..."
                if [[ "$DRY_RUN" == true ]]; then
                    echo "    [dry-run] sudo pacman -S --noconfirm $apt_pkg"
                else
                    sudo pacman -S --noconfirm "$apt_pkg"
                fi
                return
                ;;
        esac
    fi

    # Fallback to pip if available
    if [[ -n "$pip_pkg" ]]; then
        info "Installing $name via pip..."
        if [[ "$DRY_RUN" == true ]]; then
            echo "    [dry-run] $PY -m pip install $pip_pkg"
        else
            "$PY" -m pip install "$pip_pkg"
        fi
        return
    fi

    fail "Could not auto-install $name. Please install it manually."
    return 1
}

# ── Check Python ──────────────────────────────────────────────
check_python() {
    info "Checking Python..."
    if resolve_python; then
        ok "Python $("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') ($PY)"
        return 0
    fi
    warn "Python 3.11+ not found"
    read -rp "    Install Python? [Y/n] " answer </dev/tty
    answer="${answer:-Y}"
    if [[ "$answer" =~ ^[Yy] ]]; then
        # First the distro's own python3 (3.12 on Ubuntu 24.04, 3.11 on Debian
        # 12, and the only name that exists everywhere). Where that is still too
        # old (Ubuntu 22.04 ships 3.10), ask for 3.11 by name with the package
        # manager's own spelling. || true: where a package does not exist the
        # honest die below should speak, not the package manager's raw error.
        install_package "Python" "python@3.12" "python3 python3-venv" "" || true
        if ! resolve_python; then
            case "$LINUX_PKG" in
                apt) install_package "Python" "python@3.12" "python3.11 python3.11-venv" "" || true ;;
                dnf) install_package "Python" "python@3.12" "python3.11" "" || true ;;
            esac
        fi
        resolve_python || die "Python 3.11+ still not found on PATH. Install Python 3.11 or newer with your package manager (macOS: brew install python@3.12; Ubuntu 22.04: sudo apt install python3.11 python3.11-venv; Debian 11 has none, upgrade to Debian 12), open a new terminal, and re-run the installer."
    else
        die "Python 3.11+ is required. Install from https://python.org and try again."
    fi
}

# ── Check yt-dlp ──────────────────────────────────────────────
check_ytdlp() {
    info "Checking yt-dlp..."

    if command_exists yt-dlp; then
        ok "yt-dlp $(yt-dlp --version 2>/dev/null || echo '(version unknown)')"
        return 0
    fi

    warn "yt-dlp not found"
    read -rp "    Install yt-dlp? [Y/n] " answer </dev/tty
    answer="${answer:-Y}"
    if [[ "$answer" =~ ^[Yy] ]]; then
        install_package "yt-dlp" "yt-dlp" "yt-dlp" "yt-dlp"
    else
        die "yt-dlp is required for downloading videos."
    fi
}

# ── Check ffmpeg ──────────────────────────────────────────────
check_ffmpeg() {
    info "Checking ffmpeg..."

    if command_exists ffmpeg && command_exists ffprobe; then
        ok "ffmpeg $(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}' || echo '(version unknown)')"
        return 0
    fi

    warn "ffmpeg not found"
    read -rp "    Install ffmpeg? [Y/n] " answer </dev/tty
    answer="${answer:-Y}"
    if [[ "$answer" =~ ^[Yy] ]]; then
        install_package "ffmpeg" "ffmpeg" "ffmpeg" ""
    else
        die "ffmpeg is required for audio processing."
    fi
}

# ── Install anyscribe via pipx (installs pipx first if absent) ──
install_with_pipx() {
    if ! command_exists pipx; then
        info "Installing pipx..."
        if [[ "$OS" == "macos" ]]; then
            brew install pipx
        else
            case "$LINUX_PKG" in
                apt)    sudo apt update -qq && sudo apt install -y pipx ;;
                dnf)    sudo dnf install -y pipx ;;
                pacman) sudo pacman -S --noconfirm python-pipx ;;
                *)      "$PY" -m pip install --user pipx || die "Could not install pipx automatically. Install pip or pipx for $PY (https://pipx.pypa.io), then re-run the installer." ;;
            esac
        fi
    fi
    # pipx defaults to its own interpreter (3.10 on Ubuntu 22.04); install with the one
    # that passed the check. An existing anyscribe venv keeps its old Python even
    # under --force (pipx 1.0.0 only reinstalls the package), so remove it first.
    local venvs
    venvs="$(pipx environment --value PIPX_LOCAL_VENVS 2>/dev/null || echo "$HOME/.local/pipx/venvs")"
    if [[ -d "$venvs/anyscribe" ]]; then
        info "Replacing the existing pipx anyscribe so it runs on $PY..."
        pipx uninstall anyscribe || true
        [[ ! -d "$venvs/anyscribe" ]] || die "Could not remove the existing pipx anyscribe, so it would keep its old Python. Run: pipx uninstall anyscribe, then re-run the installer."
    fi
    pipx install --force --python "$(command -v "$PY")" "$1"
    pipx ensurepath 2>/dev/null || true
    USED_PIPX=true
}

# ── Check JavaScript runtime (for YouTube) ────────────────────
# yt-dlp solves YouTube's JavaScript challenges on Deno (its default) or Node
# 22+. Without one, downloads warn and may miss formats. Optional: a refusal
# only warns.
# Prints "major minor" of the first version-looking number in $1, or nothing.
semver_major_minor() { printf '%s' "$1" | grep -oE '[0-9]+\.[0-9]+' | head -1 | tr '.' ' '; }

js_runtime_found() {
    local d v major minor
    for d in "$(command -v deno 2>/dev/null || true)" "$HOME/.deno/bin/deno"; do
        [[ -n "$d" && -x "$d" ]] || continue
        v="$("$d" --version 2>/dev/null | head -1 || true)"
        [[ "$v" == deno\ * ]] || continue  # a same-named unrelated binary
        read -r major minor <<<"$(semver_major_minor "$v")"
        if [[ "$major" =~ ^[0-9]+$ && "$minor" =~ ^[0-9]+$ ]] && (( major > 2 || (major == 2 && minor >= 3) )); then
            ok "deno $major.$minor"
            return 0
        fi
        warn "$v found at $d, but yt-dlp needs Deno 2.3 or newer"
    done
    if command_exists node; then
        v="$(node --version 2>/dev/null | head -1 || true)"
        read -r major minor <<<"$(semver_major_minor "$v")"
        if [[ "$major" =~ ^[0-9]+$ ]] && (( major >= 22 )); then
            ok "node $v (yt-dlp will use it for YouTube)"
            return 0
        fi
        warn "node ${v:-(version unknown)} found, but yt-dlp needs 22 or newer"
    fi
    return 1
}

check_js_runtime() {
    info "Checking JavaScript runtime (Deno or Node, for YouTube)..."
    js_runtime_found && return 0
    warn "No supported JavaScript runtime found; YouTube downloads may miss formats or fail"
    # This step is optional: an unreadable prompt (no terminal) skips it, never aborts.
    if ! read -rp "    Install Deno? [Y/n] " answer </dev/tty; then
        warn "No terminal to ask on. Skipping; install Deno later and run: anyscribe doctor"
        return 0
    fi
    answer="${answer:-Y}"
    if [[ ! "$answer" =~ ^[Yy] ]]; then
        warn "Skipping. Install Deno later and run: anyscribe doctor"
        return 0
    fi
    if [[ "$OS" == "macos" ]] && command_exists brew; then
        if [[ "$DRY_RUN" == true ]]; then
            echo "    [dry-run] brew install deno"
        else
            brew install deno || true
        fi
    else
        # Deno publishes no apt/dnf package; its script installs to ~/.deno/bin
        # and (with --yes) adds that to the shell profile. It needs unzip.
        if [[ "$DRY_RUN" == true ]]; then
            echo "    [dry-run] curl -fsSL https://deno.land/install.sh | sh -s -- --yes"
        else
            if ! command_exists unzip && [[ "$LINUX_PKG" == "apt" ]]; then
                sudo apt update -qq && sudo apt install -y unzip || true
            fi
            curl -fsSL https://deno.land/install.sh | sh -s -- --yes || true
        fi
    fi
    if [[ "$DRY_RUN" == true ]]; then
        return 0
    fi
    js_runtime_found || warn "Deno did not install (its installer needs unzip or 7z). Install it by hand (https://docs.deno.com/runtime/getting_started/installation/) and run: anyscribe doctor"
}

# ── Install anyscribe ────────────────────────────────────────
install_anyscribe() {
    info "Installing anyscribe..."

    local pip_cmd="anyscribe[tray]"
    if [[ "$INSTALL_METHOD" == "git" ]]; then
        # git installs skip the [tray] extra — extras syntax differs for git URLs (spec §3)
        pip_cmd="git+${REPO_URL}"
    elif [[ "$INSTALL_METHOD" != "pip" ]]; then
        die "Unknown install method: $INSTALL_METHOD (use 'pip' or 'git')"
    fi

    if [[ "$DRY_RUN" == true ]]; then
        echo "    [dry-run] $PY -m pip install --upgrade $pip_cmd"
        return 0  # nothing was installed, so there is nothing to verify
    else
        # Try pip first; fall back to pipx if this Python has no pip or is
        # externally managed.
        local pip_output
        if ! "$PY" -m pip --version >/dev/null 2>&1; then
            warn "$PY has no pip. Using pipx instead..."
            install_with_pipx "$pip_cmd"
        elif pip_output=$("$PY" -m pip install --upgrade "$pip_cmd" 2>&1); then
            : # Success
        elif echo "$pip_output" | grep -qi "externally-managed"; then
            warn "System Python is externally managed. Using pipx instead..."
            install_with_pipx "$pip_cmd"
        else
            # Some other pip error
            echo "$pip_output" >&2
            die "pip install failed. See error above."
        fi
    fi

    # Verify. The command the user will type must be the copy just installed,
    # not an older anyscribe from another Python that sits earlier on PATH.
    local installed_ver="" found_ver=""
    if [[ "$USED_PIPX" == true ]]; then
        # || true: a dead or foreign copy must produce a warning, not a silent exit under set -e
        installed_ver="$("$(pipx_bin_dir)/anyscribe" --version 2>/dev/null | awk '{print $2}' || true)"
    else
        installed_ver="$("$PY" -m anyscribe --version 2>/dev/null | awk '{print $2}' || true)"
    fi
    if command_exists anyscribe; then
        found_ver="$(anyscribe --version 2>/dev/null | awk '{print $2}' || true)"
        if [[ -n "$installed_ver" && "$found_ver" != "$installed_ver" ]]; then
            warn "An older anyscribe (${found_ver:-unknown version}, $(command -v anyscribe)) is first on PATH; the new one is $installed_ver."
            echo "    Remove the old one (a pip install on Python 3.10: python3.10 -m pip uninstall anyscribe) and open a new terminal,"
            if [[ "$USED_PIPX" == true ]]; then
                echo "    or run the new one as: $(pipx_bin_dir)/anyscribe"
            else
                echo "    or run the new one as: $PY -m anyscribe"
            fi
        else
            ok "anyscribe ${found_ver:-installed}"
        fi
    elif [[ "$USED_PIPX" == true ]]; then
        warn "anyscribe installed via pipx. Restart your terminal or run: pipx ensurepath"
    else
        warn "anyscribe installed but not found in PATH."
        # Ask the interpreter we installed with which scripts dir (default or
        # user scheme) actually holds the anyscribe command.
        local scripts_dir
        scripts_dir="$("$PY" -c 'import os, sysconfig
for d in (sysconfig.get_path("scripts"), sysconfig.get_path("scripts", sysconfig.get_preferred_scheme("user"))):
    if os.access(os.path.join(d, "anyscribe"), os.X_OK):
        print(d)
        break' 2>/dev/null || true)"
        if [[ -n "$scripts_dir" ]]; then
            echo "    Try adding this to your shell profile:"
            echo ""
            echo "      export PATH=\"$scripts_dir:\$PATH\""
            echo ""
            echo "    Then restart your terminal and run: anyscribe --version"
        else
            echo "    Run it with: $PY -m anyscribe --version"
        fi
    fi
}

# pipx's bin dir, which is usually not on this shell's PATH yet (ensurepath
# only edits the profile).
pipx_bin_dir() { pipx environment --value PIPX_BIN_DIR 2>/dev/null || echo "$HOME/.local/bin"; }

# ── Run post-install action (opt-in) ─────────────────────────
run_post_install() {
    [[ "$RUN_UI" == true || "$RUN_ONBOARD" == true ]] || return 0
    # Launch the copy just installed, never whichever anyscribe PATH finds first.
    local cmd
    if [[ "$USED_PIPX" == true ]]; then
        cmd=("$(pipx_bin_dir)/anyscribe")
        if [[ ! -x "${cmd[0]}" ]]; then
            warn "Automatic launch skipped: the anyscribe executable could not be found. Run \`pipx list\` to inspect the installation."
            echo "    (looked for ${cmd[0]})"
            POST_INSTALL_SKIPPED=true
            return 0
        fi
    else
        cmd=("$PY" -m anyscribe)
    fi

    if [[ "$RUN_UI" == true ]]; then
        echo ""
        info "Launching web UI..."
        echo ""
        if [[ "$DRY_RUN" == true ]]; then
            echo "    [dry-run] ${cmd[*]} ui"
        else
            "${cmd[@]}" ui
        fi
    elif [[ "$RUN_ONBOARD" == true ]]; then
        echo ""
        info "Starting onboarding wizard..."
        echo ""
        if [[ "$DRY_RUN" == true ]]; then
            echo "    [dry-run] ${cmd[*]} onboard --skip-deps"
        else
            "${cmd[@]}" onboard --skip-deps
        fi
    fi
}

# ── Main ──────────────────────────────────────────────────────
main() {
    if [[ "$OS" == "macos" ]]; then
        install_brew_if_needed
    fi

    echo ""
    check_python
    check_ytdlp
    check_ffmpeg
    check_js_runtime

    echo ""
    install_anyscribe

    run_post_install

    echo ""
    if [[ "$POST_INSTALL_SKIPPED" != true ]] && { [[ "$RUN_ONBOARD" == true ]] || [[ "$RUN_UI" == true ]]; }; then
        echo -e "${GREEN}${BOLD}  ┌─────────────────────────────────────┐${NC}"
        echo -e "${GREEN}${BOLD}  │  anyscribe is ready!                │${NC}"
        echo -e "${GREEN}${BOLD}  │                                     │${NC}"
        echo -e "${GREEN}${BOLD}  │  anyscribe ui       web dashboard   │${NC}"
        echo -e "${GREEN}${BOLD}  │  anyscribe \"<url>\"  transcribe now  │${NC}"
        echo -e "${GREEN}${BOLD}  └─────────────────────────────────────┘${NC}"
    else
        echo -e "${GREEN}${BOLD}  ┌─────────────────────────────────────┐${NC}"
        echo -e "${GREEN}${BOLD}  │  anyscribe is installed!            │${NC}"
        echo -e "${GREEN}${BOLD}  │                                     │${NC}"
        echo -e "${GREEN}${BOLD}  │  Next step:                         │${NC}"
        echo -e "${GREEN}${BOLD}  │    anyscribe ui                     │${NC}"
        echo -e "${GREEN}${BOLD}  │                                     │${NC}"
        echo -e "${GREEN}${BOLD}  │  Opens a dashboard in your browser  │${NC}"
        echo -e "${GREEN}${BOLD}  │  to set up and start transcribing.  │${NC}"
        echo -e "${GREEN}${BOLD}  └─────────────────────────────────────┘${NC}"
        if [[ "$POST_INSTALL_SKIPPED" == true ]]; then
            echo ""
            warn "anyscribe was installed, but the launch you asked for did not run (see above)."
        fi
        if [[ "$USED_PIPX" == true ]]; then
            echo ""
            warn "Installed via pipx — if 'anyscribe' is not found, restart your terminal"
            echo "    or run: pipx ensurepath"
        fi
    fi
    echo ""
}

main
