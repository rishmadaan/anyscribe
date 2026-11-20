---
type: troubleshooting
tags: [onboarding, installer, install.sh, install.ps1, landing, web-ui, errors, providers]
tldr: "Wave 1 of the 2026-11-20 onboarding audit: the places a non-technical customer stopped cold. Homebrew under curl | bash went non-interactive and the installer died silently (now /dev/tty plus a plain stop message); Windows got a full copyable install line; installers and wizard never say ready without ffmpeg (brew install exits 0 for an unlinked formula); no-credit 402/429 insufficient_quota stops with a plain message instead of retrying; Groq/OpenRouter keys checked for real, Sarvam 'not checked'; wizard locked during the download; the installer's last box says how to open anyscribe; install.ps1 no longer exits (closing the window) under irm | iex; Read transcript and a formatted view."
---

# Onboarding wave 1: let people in

## Why

An audit of install and first run, done as a non-technical customer would meet
it (a content creator or student on a Mac or Windows laptop, never opened a
terminal, no API keys, often Hindi or Hinglish audio), found 41 problems. Six
stopped people cold. Wave 1 fixes those walls plus the finished transcript
being unreadable; waves 2 and 3 are listed in `BACKLOG.md` under "Onboarding
audit (2026-11-20)". Two builders worked in parallel on disjoint files
(installers, website and docs; Python and dashboard), sharing a list of fixed
user-facing sentences so both used the same words.

## Mechanisms worth remembering

**Homebrew under `curl | bash` (W1).** The installer ran Homebrew's installer
as `/bin/bash -c "$(curl …)"`. Its stdin is the installer's own stdin, which
under `curl | bash` is the pipe carrying the script. Homebrew checks `[[ -t 0 ]]`,
decides it is non-interactive, runs `sudo -n` (which fails with no cached
password), and aborts ("Insufficient permissions…" on Linux, "Need sudo
access on macOS" on a Mac). `set -e` then ended anyscribe's installer with no
message. Fix: `</dev/tty` on that one command, the same way every prompt in
the script already reads. Reproduced in Docker with Homebrew's Linux branch
(same check): old line refuses, new line asks for the password and finishes.
Two guards stop with a plain sentence: a non-zero exit, and no `brew`
afterwards, because a failed `curl` inside `$(…)` hands `bash -c` an empty
script, which exits 0.

**`brew install` of an unlinked formula exits 0 (W3).** Verified on Homebrew
7.0.15: `brew install hello; brew unlink hello; brew install hello` prints
"already installed, it's just not linked" and exits 0, and `hello` is not on
PATH. So "the package manager succeeded" does not mean "ffmpeg is there";
`install.sh` now looks again after installing and ends with "anyscribe is
installed, but can't transcribe yet" instead of "ready". In the unlinked case
the fix is `brew link ffmpeg`, which brew prints itself.

**`install.ps1` already refreshed PATH after winget (W3).** The audit thought
a fresh winget ffmpeg was invisible to the running session. `Refresh-Path`
(Machine + User PATH from the registry) already ran after both winget and
Chocolatey. The real bug was that the script never recorded the outcome, so a
failed or skipped ffmpeg install still ended with "anyscribe is ready!".

**`exit` under `irm | iex` (W7).** `Invoke-Expression` runs the text in the
person's own session, so `exit 1` in the catch block closed their whole
PowerShell window and the error with it. The script now ends without `exit`
(nothing follows the catch block) and keeps `exit 1` only when
`$PSCommandPath` is set, that is, when it runs as a `.ps1` file. Checked on
the official PowerShell 7.4 image: the session survives and runs the next
command; `pwsh -File` still exits 1. Not checked on Windows PowerShell 5.1.

**Which terminal can run `anyscribe` (W7).** The installer is a child of the
person's shell, so `pipx ensurepath` only helps new windows. `install.sh`
saves `$PATH` at start (`ORIG_PATH`, before any Homebrew `shellenv`) and asks
whether that PATH finds `anyscribe`; if not and pipx was used, the box says
to open a new terminal window and prints the full path for this one. On
Windows the PATH changes happen in the person's own session under `iex`, so
only the python `-m` fallback is needed.

**No credit (W4).** OpenAI answers an account with no credit with HTTP 429
and `insufficient_quota`; OpenRouter answers 402. Both were "Rate limited,
wait and retry" and retried. They are now a non-retryable `NoCreditError`
with the billing link (OpenAI) and the free local option. Ordinary 429s still
retry.

**Key checks (W5).** Groq's check returned "API key is set" without a call,
Sarvam's the same, and OpenRouter called `/api/v1/models`, which answers 200
with no key at all, so any text was "valid". Groq now calls
`/openai/v1/models` and OpenRouter `/api/v1/key` with the key; Sarvam has no
way to check a key without spending, so it says "Saved, not checked" in amber.

## Decisions

- Website: two stacked blocks, not tabs, in the hero: the page's tab script
  is global and would also switch the install section's tabs; both blocks
  visible means no hidden state for a first-time visitor.
- The installer's end box is drawn by a small `box` helper that wraps text with
  `fold -s` (available on macOS and Linux), so the fixed sentences fit without
  hand-made line breaks.
- macOS wording for "click the app": desktop mode puts it in `~/Applications`,
  so the box says "the Applications folder inside your home folder", not "your
  Applications folder" (that is `/Applications`).
- The Linux ffmpeg command in the box follows the detected package manager
  (`apt`, `dnf`, `pacman`).

## Known limits

- With no terminal at all (`curl | bash` from a script with no TTY), the
  installer's first `[Y/n]` prompt fails to open `/dev/tty` and the script
  stops with bash's own error. Pre-existing, unchanged.
- The macOS branches were exercised on Linux (Homebrew's Linux installer has
  the same non-interactive check; the end box via `--dry-run` with `uname`
  answering Darwin), not on a real Mac.
