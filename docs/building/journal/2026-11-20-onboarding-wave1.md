---
type: troubleshooting
tags: [onboarding, installer, install.sh, install.ps1, landing, web-ui, errors, providers]
tldr: "Wave 1 of the 2026-11-20 onboarding audit: the places a non-technical customer stopped cold. Homebrew under curl | bash went non-interactive and the installer died silently (now /dev/tty plus a plain stop message); Windows got a full copyable install line; installers and wizard never say ready without ffmpeg (brew install exits 0 for an unlinked formula); no-credit 402/429 insufficient_quota stops with a plain message instead of retrying; Groq/OpenRouter keys checked for real, Sarvam 'not checked'; closing the wizard during the download asks first (a hard lock in PR #26, replaced in the follow-up); the installer's last box says how to open anyscribe; install.ps1 no longer exits (closing the window) under irm | iex; Read transcript and a formatted view."
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

**The download lock (W6) took three rounds.** "Is a setup running" had two
copies (the wizard's and the local step's) and about nine writers, and the
page learns the answer from status reads that can fail, hang or land late.
Each writer handled only the outcomes its author walked, so round 1 unlocked
on a failed read and round 2 stayed locked forever on one. The shape that
holds: the local step alone owns it (one effect reports idle, running or
unknown to the wizard); status is read one request at a time, each with a
10 s limit (`AbortController`, not `AbortSignal.timeout`), separately from
the log; watching ends only on a good read, sent after the start request
settled, that says the setup stopped; a start that got a 409 or no answer at
all is watched, not reported as failed. When two reads in a row fail, the
step says "Can't reach anyscribe right now" and the wizard can close after
one confirmation: a hard lock with no exit while the server is unreachable
traps the customer. The server keeps setup state in memory, so after a
restart it says "not running, no error"; the step's runnable check turns
that into "can't run yet, Try again", never "ready".

**Key checks (W5).** Groq's check returned "API key is set" without a call,
Sarvam's the same, and OpenRouter called `/api/v1/models`, which answers 200
with no key at all, so any text was "valid". Groq now calls
`/openai/v1/models` and OpenRouter `/api/v1/key` with the key; Sarvam has no
way to check a key without spending, so it says "Not checked yet" in amber.

## Decisions

- Website: two stacked blocks, not tabs, in the hero: the page's tab script
  is global and would also switch the install section's tabs; both blocks
  visible means no hidden state for a first-time visitor.
- The installer's end box is drawn by a small `box` helper that wraps text with
  `fold -s` (available on macOS and Linux), so the fixed sentences fit without
  hand-made line breaks.
- macOS wording for "click the app": desktop mode puts it in `~/Applications`,
  which Finder's sidebar "Applications" (`/Applications`) is not, so the box
  says "press Cmd and Space, type anyscribe, press Return" (Spotlight indexes
  `~/Applications`). Plain "Cmd", not the symbol, keeps the box aligned. The
  first draft said "the Applications folder inside your home folder"; the
  round 1 review found a non-technical Mac user would not find that folder.
- The Linux ffmpeg command in the box follows the detected package manager
  (`apt`, `dnf`, `pacman`).
- W6 shipped the owner's hard lock while the page can confirm the download
  runs; the round 2 diagnosis recommended confirm-to-close instead, and the
  owner chose it after the review cap (see the follow-up below).
- On Windows the ffmpeg notice and the installer's box say to quit anyscribe
  from the tray and open it again: the running tray keeps the PATH it started
  with, so Check again can't see a fresh winget install.

## Known limits

- With no terminal at all (`curl | bash` from a script with no TTY), the
  installer's first `[Y/n]` prompt fails to open `/dev/tty` and the script
  stops with bash's own error. Pre-existing, unchanged.
- The macOS branches were exercised on Linux (Homebrew's Linux installer has
  the same non-interactive check; the end box via `--dry-run` with `uname`
  answering Darwin), not on a real Mac.

## Follow-up (2026-11-20): closing asks first

PR #26 shipped W6 as a hard lock: during the download, Escape, a click
outside and Skip did nothing while anyscribe answered. The round 2 diagnosis
(`docs/reviews/2026-11-20-onboarding-wave1/diagnosis-r2.md`, section 4)
showed why the lock kept failing review: it can only be released by "the
server says the setup stopped", the page learns that through reads that can
fail, hang or land late, and the server has no cancel, so every round moved
the defect between "unlocks during a live download" and "holds the customer
with no way out". The owner chose its design B after the review cap: closing
is allowed after a warning.

- **Never locked.** `disableClose` is `saving` only and Skip for now shows on
  every step. While the local step watches a setup (or its start request is
  in flight), Escape, a click outside and Skip open "Close setup? The download
  keeps going in the background while anyscribe stays open. …" with **Keep
  setting up** (focused, which also scrolls it into view) and **Close setup**
  (closes without the dismissed flag, so the wizard returns). A wrong belief
  about "is a setup running" now costs one extra or one missing question,
  never a trap.
- **Adoption (R3C1).** The wizard's opening read saw `setup_running: true` but
  the step started idle until its own first read, so the first moment (or a
  hung read) let Escape close at once. The wizard now hands that knowledge to
  the step it routes to, which watches from its first render; it is cleared
  when that step is left, so it is used once.
- **Start lifetime (R3C2).** A status read sent before the start request
  settled could start watching and then complete the step before the start
  answered. A counter that moves when the start is sent and again when it
  settles now makes such a read say nothing about that setup.
- **Quitting stops the download.** Setup runs inside the anyscribe process and
  its state is in memory (`web/routes/local.py`), so the unreachable notice no
  longer promises the download carries on after quitting. A restarted server
  answers "not running, no outcome, no error"; the step now says "The setup
  stopped before it finished, because anyscribe was closed. Click Try again to
  start it again." instead of a missing-part sentence.
- **No resume across a restart.** A real Whisper Base download stopped at
  35.6% left 0 bytes of the weights on disk (huggingface_hub 2.4 with hf_xet
  writes them at the end), and Try again started again from 0%. So the new
  sentences say "start it again", not "carries on". The model card's
  "incomplete: the download resumes" and troubleshooting's "picks up where it
  stopped" predated this; the review's round 1 changed them to "incomplete:
  setup downloads it again" and "the download starts again" (with Settings'
  button, now "Incomplete: download again", and the same claim in the
  configuration page and the skill's command reference). `anyscribe model
  info`'s "Resume the download" line is server-side code and a wave 2 item.
