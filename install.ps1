# ──────────────────────────────────────────────────────────────
# anyscribe installer for Windows
#
# Usage (PowerShell):
#   irm https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.ps1 | iex
#
# What it does:
#   1. Checks for Python 3.11+, offers to install via winget
#   2. Checks for ffmpeg, offers to install via winget/choco
#   3. Installs yt-dlp via pip
#   4. Installs anyscribe (with menu-bar tray) via pip
#   5. Fixes PATH so `anyscribe` works from any terminal
#   6. Tells you to run `anyscribe ui`
# ──────────────────────────────────────────────────────────────

$ErrorActionPreference = 'Stop'

# ── Helpers ───────────────────────────────────────────────────

function Write-Banner {
    Write-Host ""
    Write-Host "  +-------------------------------------+" -ForegroundColor White
    Write-Host "  |       anyscribe installer           |" -ForegroundColor White
    Write-Host "  |  Video -> Transcript -> Markdown    |" -ForegroundColor White
    Write-Host "  +-------------------------------------+" -ForegroundColor White
    Write-Host ""
}

function Write-Info($msg)    { Write-Host "==> $msg" -ForegroundColor Blue }
function Write-Ok($msg)      { Write-Host "  + $msg" -ForegroundColor Green }
function Write-Warn($msg)    { Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Fail($msg)    { Write-Host "  x $msg" -ForegroundColor Red }

function Test-CommandExists($cmd) {
    $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Refresh-Path {
    # Reload PATH from registry so newly installed tools are found
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machinePath;$userPath"
}

# ── Check Python ──────────────────────────────────────────────

function Test-Python {
    Write-Info "Checking Python..."

    # Windows uses 'python' (not 'python3') when installed from python.org;
    # 'py' is the python.org launcher, which picks the newest installed Python.
    foreach ($cmd in @('python', 'python3', 'py')) {
        if (Test-CommandExists $cmd) {
            try {
                $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                $parts = $ver.Split('.')
                $major = [int]$parts[0]
                $minor = [int]$parts[1]
                if ($major -ge 3 -and $minor -ge 11) {
                    Write-Ok "Python $ver ($cmd)"
                    # Keep the exact interpreter, not the name: Refresh-Path later
                    # rebuilds PATH with machine entries first, which can re-point
                    # `python` at an older install.
                    $script:PythonCmd = (& $cmd -c "import sys; print(sys.executable)" 2>$null).Trim()
                    return
                } else {
                    Write-Warn "Python $ver found, but 3.11+ is required"
                }
            } catch {
                # Not a valid Python
            }
        }
    }

    Write-Warn "Python 3.11+ not found"

    if (Test-CommandExists 'winget') {
        Write-Host "    Install Python 3.12 via winget? [Y/n] " -NoNewline
        $answer = Read-Host
        if ($answer -eq '' -or $answer -match '^[Yy]') {
            Write-Info "Installing Python via winget..."
            winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
            Refresh-Path
            # Re-check the version: an older all-users Python earlier on PATH
            # still answers to `python` after a per-user winget install.
            foreach ($cmd in @('python', 'python3', 'py')) {
                if (Test-CommandExists $cmd) {
                    try {
                        $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                        $parts = $ver.Split('.')
                        if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 11) {
                            Write-Ok "Python $ver ($cmd)"
                            $script:PythonCmd = (& $cmd -c "import sys; print(sys.executable)" 2>$null).Trim()
                            return
                        }
                    } catch {
                        # Not a valid Python
                    }
                }
            }
            Write-Warn "Python 3.11+ still not found after the winget step (an older Python may be first on PATH, or winget failed). Open a new terminal and re-run, or remove the old Python from PATH."
        }
    }

    Write-Fail "Python 3.11+ is required. Install from https://python.org"
    throw "Python not found"
}

# ── Check ffmpeg ──────────────────────────────────────────────

function Test-Ffmpeg {
    Write-Info "Checking ffmpeg..."

    if ((Test-CommandExists 'ffmpeg') -and (Test-CommandExists 'ffprobe')) {
        Write-Ok "ffmpeg found"
        return
    }

    Write-Warn "ffmpeg not found"

    if (Test-CommandExists 'winget') {
        Write-Host "    Install ffmpeg via winget? [Y/n] " -NoNewline
        $answer = Read-Host
        if ($answer -eq '' -or $answer -match '^[Yy]') {
            Write-Info "Installing ffmpeg via winget..."
            winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
            Refresh-Path
            if (Test-CommandExists 'ffmpeg') {
                Write-Ok "ffmpeg installed"
                return
            }
        }
    }

    if (Test-CommandExists 'choco') {
        Write-Host "    Install ffmpeg via Chocolatey? [Y/n] " -NoNewline
        $answer = Read-Host
        if ($answer -eq '' -or $answer -match '^[Yy]') {
            Write-Info "Installing ffmpeg via Chocolatey..."
            choco install ffmpeg -y
            Refresh-Path
            if (Test-CommandExists 'ffmpeg') {
                Write-Ok "ffmpeg installed"
                return
            }
        }
    }

    Write-Warn "Could not auto-install ffmpeg."
    Write-Host "    Download manually from: https://www.gyan.dev/ffmpeg/builds/"
    Write-Host "    Or install winget/chocolatey and re-run this script."
    Write-Host ""
}

# ── Check JavaScript runtime (for YouTube) ───────────────────
# yt-dlp solves YouTube's JavaScript challenges on Deno (its default) or Node
# 22+. Optional: a failure only warns.

# Bounded probe: the program's first stdout line when it exits 0 within 10 s, else $null.
function Get-VersionLine($exe, $argument) {
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $exe
        $psi.Arguments = $argument
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $p = [System.Diagnostics.Process]::Start($psi)
        $out = $p.StandardOutput.ReadToEndAsync()
        $null = $p.StandardError.ReadToEndAsync()  # drain it, or a chatty program blocks on a full pipe
        if (-not $p.WaitForExit(10000)) { try { $p.Kill() } catch {}; return $null }
        if ($p.ExitCode -ne 0) { return $null }
        return (($out.Result -split "`r?`n")[0]).Trim()
    } catch { return $null }
}

function Test-JsRuntime {
    Write-Info "Checking JavaScript runtime (Deno or Node, for YouTube)..."
    # Optional step: any failure inside only warns and returns.
    try {
        if (Test-CommandExists 'deno') {
            $denoVer = Get-VersionLine 'deno' '--version'
            if ($denoVer -and $denoVer -match '^deno (\d+)\.(\d+)\.') {
                if ([int]$Matches[1] -gt 2 -or ([int]$Matches[1] -eq 2 -and [int]$Matches[2] -ge 3)) {
                    Write-Ok "deno $($Matches[1]).$($Matches[2])"
                    return
                }
                Write-Warn "deno $($Matches[1]).$($Matches[2]) found, but yt-dlp needs 2.3 or newer"
            } else {
                Write-Warn "deno found, but its version could not be read"
            }
        }
        if (Test-CommandExists 'node') {
            $nodeVer = Get-VersionLine 'node' '--version'
            if ($nodeVer -and $nodeVer -match '^v(\d+)\.(\d+)\.(\d+)(-[\w.]+)?$') {
                if ([int]$Matches[1] -ge 22) {
                    Write-Ok "node $nodeVer (yt-dlp will use it for YouTube)"
                    return
                }
                Write-Warn "node $nodeVer found, but yt-dlp needs 22 or newer"
            } else {
                Write-Warn "node found, but its version could not be read (yt-dlp needs 22 or newer)"
            }
        }

        Write-Warn "No supported JavaScript runtime found; YouTube downloads may miss formats or fail"
        if (Test-CommandExists 'winget') {
            Write-Host "    Install Deno via winget? [Y/n] " -NoNewline
            $answer = Read-Host
            if ($answer -eq '' -or $answer -match '^[Yy]') {
                Write-Info "Installing Deno via winget..."
                winget install DenoLand.Deno --accept-package-agreements --accept-source-agreements
                Refresh-Path
                if (Test-CommandExists 'deno') {
                    Write-Ok "deno installed"
                    return
                }
            }
        }
        Write-Warn "Deno not installed. Install it from https://docs.deno.com/runtime/getting_started/installation/ and run: anyscribe doctor"
    } catch {
        Write-Warn "Could not check or install a JavaScript runtime ($_). Install Deno from https://docs.deno.com/runtime/getting_started/installation/ and run: anyscribe doctor"
    }
}

# ── Check yt-dlp ──────────────────────────────────────────────

function Test-YtDlp {
    Write-Info "Checking yt-dlp..."

    try {
        $null = & $script:PythonCmd -m yt_dlp --version 2>$null
        Write-Ok "yt-dlp found"
        return
    } catch {}

    Write-Warn "yt-dlp not found. Installing via pip..."
    & $script:PythonCmd -m pip install --quiet yt-dlp
    Write-Ok "yt-dlp installed"
}

# ── Install anyscribe ─────────────────────────────────────────

function Install-Anyscribe {
    Write-Info "Installing anyscribe..."
    & $script:PythonCmd -m pip install --quiet --upgrade "anyscribe[tray]"
    if ($LASTEXITCODE -ne 0) { throw "pip install failed (exit $LASTEXITCODE)" }

    # Verify. The command the user will type must be the copy just installed,
    # not an older anyscribe.exe from another Python earlier on PATH.
    # try/catch: under ErrorActionPreference Stop, a native command writing to
    # stderr can throw even with 2>$null; a probe failure must not abort here.
    $installedVer = try { (& $script:PythonCmd -m anyscribe --version 2>$null | Out-String).Trim() } catch { '' }
    if (-not $installedVer) {
        throw "anyscribe was installed but `"$script:PythonCmd -m anyscribe --version`" did not run"
    }
    Refresh-Path
    if (Test-CommandExists 'anyscribe') {
        $foundVer = try { (anyscribe --version 2>$null | Out-String).Trim() } catch { '' }
        if ($foundVer -ne $installedVer) {
            Write-Warn "An older anyscribe ($(if ($foundVer) { $foundVer } else { 'unknown version' })) is first on PATH: $((Get-Command anyscribe).Source). The new one is $installedVer."
            Write-Host "    Remove it (py -3.10 -m pip uninstall anyscribe) and open a new terminal, or run the new one as: & `"$script:PythonCmd`" -m anyscribe ui" -ForegroundColor Yellow
            Fix-Path
        } else {
            Write-Ok "anyscribe installed ($foundVer)"
        }
    } else {
        Write-Ok "anyscribe package installed"
        Fix-Path
    }
}

# ── Fix PATH ──────────────────────────────────────────────────

function Fix-Path {
    Write-Info "Checking PATH..."

    try {
        $scriptsDir = & $script:PythonCmd -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>$null
    } catch {
        Write-Warn "Could not detect Python scripts directory"
        return
    }

    if (-not $scriptsDir) { return }

    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($userPath -and $userPath.Contains($scriptsDir)) {
        Write-Ok "Scripts directory already in PATH"
        return
    }

    Write-Warn "Adding $scriptsDir to your PATH..."
    $newPath = if ($userPath) { "$userPath;$scriptsDir" } else { $scriptsDir }
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    $env:Path = "$env:Path;$scriptsDir"
    Write-Ok "PATH updated (takes effect in new terminals)"
}

# ── Main ──────────────────────────────────────────────────────

$script:PythonCmd = 'python'

Write-Banner

try {
    Test-Python
    Test-Ffmpeg
    Test-JsRuntime
    Test-YtDlp
    Write-Host ""
    Install-Anyscribe

    Write-Host ""
    Write-Host "  +-------------------------------------+" -ForegroundColor Green
    Write-Host "  |  anyscribe is installed!            |" -ForegroundColor Green
    Write-Host "  |                                     |" -ForegroundColor Green
    Write-Host "  |  Next step:                         |" -ForegroundColor Green
    Write-Host "  |    anyscribe ui                     |" -ForegroundColor Green
    Write-Host "  |                                     |" -ForegroundColor Green
    Write-Host "  |  Opens a dashboard in your browser  |" -ForegroundColor Green
    Write-Host "  |  to set up and start transcribing.  |" -ForegroundColor Green
    Write-Host "  +-------------------------------------+" -ForegroundColor Green
    Write-Host ""

    if (-not (Test-CommandExists 'anyscribe')) {
        Write-Warn "If 'anyscribe' is not recognized, use:"
        Write-Host "    & `"$script:PythonCmd`" -m anyscribe ui" -ForegroundColor Cyan
        Write-Host ""
    }
} catch {
    Write-Fail "Installation failed: $_"
    Write-Host ""
    Write-Host "  Manual install:" -ForegroundColor Yellow
    Write-Host "    1. Install Python 3.11+ from https://python.org" -ForegroundColor Yellow
    Write-Host "    2. pip install anyscribe" -ForegroundColor Yellow
    Write-Host "    3. Install ffmpeg from https://www.gyan.dev/ffmpeg/builds/" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
