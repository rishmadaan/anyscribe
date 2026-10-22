You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #20 "Require Python 3.11, add Starlette and FastAPI
security floors (0.17.0 prep)", branch release/python-3.11-starlette-floor, head
commit 6ee52d746faabf63e03cb7764b06bab475e162de (round 2; round 1 reviewed c791f91), against main ecd2899
(v0.16.5 plus the five merged audit PRs #15 to #19). Checkout to read:
<checkout> (a detached clone at that commit). The full diff against main is at
<run-folder>/diff-r2.patch; the round-1 fix commit alone is at <run-folder>/fixes-r2.patch. The
lead's evidence is at <run-folder>/lead-evidence-r2.md (claims to check where you can).
Round-1 reports: <run-folder>/report-gpt-6-astra-r1.md (correctness) and
<run-folder>/report-opus-5.5-r1.md (fit).

WHY IT EXISTS (the owner's ask, in his words, 2026-10-22, answering four
decisions left open by the audit): "1. yes cut a release" ... "3. go with your
recommendation now, should do it not itself before release" (dropping Python
3.10) ... "4. go with your recommendation now, should do it not itself before
release" (a direct starlette>=1.3.1 floor). The yt-dlp JavaScript runtime
question (item 2) is still open and deliberately NOT in this PR. The release
(version bump to 0.17.0, tag, PyPI publish) happens after merge via
scripts/release.sh, which edits src/anyscribe/__init__.py and pyproject.toml;
this PR leaves the version at 0.16.5 and already carries the "## 0.17.0"
CHANGELOG entry that scripts/check-docs.py will demand once bumped.
FIRST QUESTION: is this the job he asked for, and the right instrument for it?
If the brief, the goal or the spec is wrong, say so instead of reviewing around it.

MUST NEVER HAPPEN: the published 0.17.0 fails to install on Python 3.11 to
3.14 because the pins cannot resolve; a 3.10 user gets a broken upgrade instead
of being held on 0.16.5; a user-visible string still says 3.10+; the
installers' version checks reject a valid Python, accept an invalid one, or
install anyscribe with a Python other than the one that passed the check; CI,
publish.yml or check-docs.py fails on this SHA or after the bump; CHANGELOG
claims something the merged code does not do; "0.17.0" placed where
check-docs.py would flag it before the bump (docs/user, landing, README.md,
src/anyscribe/skill).
SETTLED, DO NOT REOPEN: dropping 3.10 and adding the Starlette floor are the
owner's decisions; the yt-dlp runtime is out of scope; house style uses em
dashes in the repo's own docs; the 2026-10-21 audit journal is append-only and
untouched; the BACKLOG 0.17.0 row says "publication pending" on purpose and
flips after the tag.

PRIOR ROUNDS. Round 1 (c791f91): Astra NOT YET, Opus CONDITIONAL. Findings and
the builder's responses (claims; verify each):
- Astra I1 / Opus I2 pipx installs with its own interpreter: FIXED, install.sh
  install_with_pipx now runs `pipx install --python "$(command -v "$PY")" "$1"`.
- Astra I2 / Opus I3 install.ps1 accepts whatever `python` resolves to after
  winget: FIXED, the post-winget block re-runs the version test over python and
  python3 and warns honestly when none qualifies.
- Astra I3 / Opus I9 candidate list lacks python3.14: FIXED.
- Opus I1 Ubuntu 22.04 loop (apt install python3 installs nothing, die text
  false): FIXED, apt is asked for "python3.11 python3.11-venv" (install_package's
  apt branch now word-splits $apt_pkg on purpose) and the die text names the
  cause and the way out.
- Opus I4 getting-started Linux fix leaves 3.10 on 22.04: FIXED, paragraph added
  and HTML regenerated.
- Opus I5 CHANGELOG Breaking bullet: FIXED with the reviewer's wording.
- Astra I4 skill-refresh promise: FIXED with the reviewer's wording (normal
  commands refresh, --version and --help do not, install-skill --force).
- Opus I6 CHANGELOG wording nits (floor jargon, 3.14 line, hint wording,
  --clipboard, "about 40"): FIXED ("dozens of corrections").
- Opus I7 journal tldr: FIXED ("three of the four questions").
- Opus I8 ruff target-version py310: FIXED (py311), ruff still clean.
- Astra I6 / Opus I10 FastAPI comment overstated and 0.136 unproven: FIXED and
  CORRECTED by the lead: PyPI shows 0.133.0 is the first open-ended pin, so the
  floor is now fastapi>=0.133; comments, BACKLOG, index and journal reworded to
  "FastAPI's pin still permits versions below 1.3.1; the direct floor excludes
  them".
- Astra I5 BACKLOG "Released (current)" before the tag: FIXED ("Prepared
  2026-10-22; publication pending"; 0.16.5 keeps "(current)").
- Opus answers: BACKLOG open list relabelled "Carried forward, not in 0.17.0".
- Astra brief correction (14 files, not 13): accepted.
- Astra's broader dry runs: run by the lead on 3.11, 3.12, 3.13, 3.14 with
  every extra (lead evidence).
- DECLINED-OK: real Ubuntu 22.04 / Windows installer runs (no such machines
  here; traced only; listed to the owner as not exercised).

SOURCES: the checkout (pyproject.toml, .github/workflows/ci.yml and
publish.yml, install.sh, install.ps1, src/anyscribe/core/deps.py,
src/anyscribe/cli/main.py, src/anyscribe/cli/skill_cmd.py, README.md,
CONTRIBUTING.md, docs/user/getting-started.md, landing/index.html,
landing/docs/getting-started.html, CHANGELOG.md, BACKLOG.md,
docs/building/_index.md,
docs/building/journal/2026-10-22-v0170-python-311-starlette-floor.md,
scripts/release.sh, scripts/check-docs.py); both patches; the lead evidence;
the round-1 reports.

LENS (Every review): Is this the job he asked for? Use it the way he will:
./scripts/release.sh 0.17.0 after merge, then the publish workflow. Claims
worded stronger than their evidence.
LENS (Code PR, round 2): mark every round-1 finding FIXED / PARTLY / NOT FIXED
/ DECLINED-OK with one line of evidence each, then hunt for NEW defects the
fixes introduced. Concrete probes: install.sh install_package's apt branch now
runs `sudo apt install -y $apt_pkg` unquoted; trace every caller
(Python, pipx, ffmpeg, yt-dlp, git...) and say whether any passes a value where
word-splitting or globbing changes meaning; the --dry-run echo path too. On
Debian 11 (no python3.11 package) and Fedora/Arch (dnf/pacman branches take
"$apt_pkg"?) what happens now? `pipx install --python`: does the apt-shipped
pipx on Ubuntu 22.04 (pipx 1.0.0) accept --python, and does
`command -v "$PY"` give a path pipx accepts? install.ps1: does the new
block parse (braces, try/catch, quoting of the f-string inside double quotes,
$parts indexing when $ver is empty)? Does the warn-and-fall-through now reach
the right Write-Fail / throw? CHANGELOG: is every sentence true of main plus
this PR (check "dozens", the pipx sentence, the skill-refresh sentence against
cli/main.py:56-113 and skill_cmd.py)? pyproject: fastapi>=0.133 and
starlette>=1.3.1 with the lead's dry-run evidence; any pin that now contradicts
another. check-docs.py: simulate the bump to 0.17.0 in memory and confirm no
offenders and the CHANGELOG heading matches.

YOU MAY RUN: read-only commands only (cat, grep, sed -n, git log/show/diff on
the checkout, python -c for parsing). YOU MAY NOT: run pytest, builds,
installs, pip, servers, network calls, or anything that writes. Name any check
you could not run as an exact command so the lead can run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round-1 finding as FIXED / PARTLY / NOT FIXED / DECLINED-OK, one line
   of evidence each; then NEW defects the fixes introduced.
3. Findings, most severe first, numbered I1, I2...: severity (blocker /
   should-fix / nit, only these words); CONFIRMED or PLAUSIBLE; where
   (file:line); what goes wrong, as a concrete scenario; the fix (exact
   replacement wording for docs).
4. Answers to any questions in this brief (advice, not findings).
5. Pending owner checks: things only the owner can confirm. They do not block
   the verdict.
6. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
