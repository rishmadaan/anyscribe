You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #20 "Require Python 3.11, add Starlette and FastAPI
security floors (0.17.0 prep)", branch release/python-3.11-starlette-floor, head
commit ce39489d6c8bb6c19007d2f5e433552ca917e637 (round 4, the last round; rounds 1 to 3 reviewed c791f91, 6ee52d7,
a29d340), against main ecd2899 (v0.16.5 plus the five merged audit PRs #15 to
#19). Checkout to read: <checkout> (a detached clone at that commit). Full diff
against main: <run-folder>/diff-r4.patch; the round-3 fix commit alone: <run-folder>/fixes-r4.patch.
Lead evidence (the Docker transcripts are primary sources): <run-folder>/lead-evidence-r4.md.
Round-3 reports: <run-folder>/report-gpt-6-astra-r3.md (correctness), <run-folder>/report-opus-5.5-r3.md
(fit). Earlier rounds: <run-folder>/report-gpt-6-astra-r1.md, r2; <run-folder>/report-opus-5.5-r1.md, r2.

WHY IT EXISTS (the owner's ask, in his words, 2026-10-22): "1. yes cut a
release" ... "3. go with your recommendation now, should do it not itself
before release" (dropping Python 3.10) ... "4. go with your recommendation now,
should do it not itself before release" (a direct starlette>=1.3.1 floor). The
yt-dlp JavaScript runtime question (item 2) is still open and deliberately NOT
in this PR. The release (bump to 0.17.0, tag, PyPI publish) happens after merge
via scripts/release.sh; this PR leaves the version at 0.16.5 and carries the
"## 0.17.0" CHANGELOG entry.
FIRST QUESTION: is this the job he asked for, and the right instrument for it?
If the brief, the goal or the spec is wrong, say so instead of reviewing around it.

MUST NEVER HAPPEN: 0.17.0 fails to install on Python 3.11 to 3.14; a 3.10 user
gets a broken upgrade instead of being held on 0.16.5; a user-visible string
still says 3.10+; an installer rejects a valid Python, accepts an invalid one,
installs anyscribe with a Python other than the one that passed its check, or
reports success while an older copy is what the user's command runs; CI,
publish.yml or check-docs.py fails on this SHA or after the bump; CHANGELOG or
the skill claims something the code does not do.
SETTLED, DO NOT REOPEN: the two owner decisions; yt-dlp out of scope; em dashes
in the repo's docs are house style; the 2026-10-21 audit journal is
append-only; BACKLOG's 0.17.0 row says "publication pending" on purpose;
Ubuntu 22.04's python3.11 apt package is 3.11.0rc1 and pip's requires-python
check compares sys.version_info[:3]; the pre-existing install.ps1 "exit 1"
under "irm | iex" is a recorded follow-up; 3.10 users being held silently on
0.16.5 is a product call listed to the owner, not a defect here.

PRIOR ROUND (round 3) findings and the builder's responses (claims; verify):
- Astra I1 / Opus I1 (installers verify and launch whichever anyscribe PATH
  finds): FIXED. install.sh compares the version of the copy just installed
  (pipx bin dir copy, or "$PY -m anyscribe") with "anyscribe --version" from
  PATH and warns with the path when they differ; run_post_install launches the
  installed copy only (pipx bin or "$PY -m anyscribe"), never PATH's.
  install.ps1 does the same comparison after Refresh-Path and prints the
  shadowing copy's Source.
- Astra I2 (Debian 12 manual route into externally-managed pip): FIXED.
  getting-started step 2 Linux installs "ffmpeg pipx" (no separate yt-dlp,
  anyscribe pulls it in); step 3 has a Linux block using
  "pipx install --python /usr/bin/python3.11" with the Debian 12 / Ubuntu 24.04
  note; step 1's paragraph explains that apt's python3.11 does not change pip.
- Astra I3 (pipx --force migration unproven): the reviewer was RIGHT: the
  probe shows --force keeps the 3.10 venv. FIXED by "pipx uninstall anyscribe"
  when "pipx list" shows it, before the install; reproduced end to end (lead
  evidence).
- Astra I4 / Opus I2 (CHANGELOG "newest Python", "next command", upgrade route
  that fails on apt python3.11 and Homebrew): FIXED with the fit reviewer's
  Breaking bullet (installer route, PATH check, uninstall of the old copy,
  add-ons note) and "migrate" added to the skill-refresh sentence.
- Opus I3 (skill says plain pip install; no troubleshooting entry): FIXED.
  SKILL.md "If not installed" line checks python3 --version first; new entry
  "anyscribe update says up to date, but newer releases exist" in
  skill/references/troubleshooting.md and docs/user/troubleshooting.md
  (HTML regenerated).
- Opus I4 (commands in prose): FIXED by the step-3 Linux code block; step 1
  keeps one inline command.
- Opus I5 (die text): FIXED with the given wording.
- Opus I6 (journal lacks installer decisions): FIXED, bullet added and later
  corrected for the pipx uninstall finding.
- DECLINED-OK: Windows, dnf, pacman, macOS real runs (none available here;
  disclosed to the owner).

SOURCES: the checkout (install.sh, install.ps1, pyproject.toml,
.github/workflows/ci.yml and publish.yml, src/anyscribe/core/deps.py,
src/anyscribe/cli/main.py, src/anyscribe/cli/skill_cmd.py,
src/anyscribe/core/updater.py, src/anyscribe/skill/SKILL.md,
src/anyscribe/skill/references/troubleshooting.md, README.md, CONTRIBUTING.md,
docs/user/getting-started.md, docs/user/troubleshooting.md, landing/index.html,
landing/docs/getting-started.html, landing/docs/troubleshooting.html,
CHANGELOG.md, BACKLOG.md, docs/building/_index.md,
docs/building/journal/2026-10-22-v0170-python-311-starlette-floor.md,
scripts/release.sh, scripts/check-docs.py, tests/test_skill_license.py); both
patches; the lead evidence and Docker transcripts; the prior reports.

LENS (Every review): Is this the job he asked for? Use it the way he will:
./scripts/release.sh 0.17.0 after merge, then the publish workflow; a 3.10 user
reads the CHANGELOG and follows it; Claude Code reads the skill on a 3.10
machine. Claims worded stronger than their evidence.
LENS (Code PR, round 4): mark every round-3 finding FIXED / PARTLY / NOT FIXED
/ DECLINED-OK with one line of evidence each; then hunt for NEW defects the
round-3 fixes introduced. Concrete probes: install.sh verification block: when
"$PY -m anyscribe --version" fails (fresh pip install into a Python whose
user scripts dir is not on PATH), what prints; is installed_ver empty and does
the comparison then fall into the "ok" branch wrongly; the pipx_bin_dir
function is defined after install_anyscribe in the file but called from it:
fine in bash (functions resolve at call time), confirm. "pipx list | grep
'package anyscribe '": does pipx 1.0.0's list format contain that string (the
upgrade transcript shows the info line fired); could it match a different
package. install.ps1 verification: "& $script:PythonCmd -m anyscribe --version
2>$null | Out-String" on a failed import yields "" and the comparison is
skipped, confirm; "(Get-Command anyscribe).Source" exists in Windows
PowerShell 5.1. Docs: read getting-started steps 1 to 3 as an Ubuntu 22.04
reader, a Debian 12 reader, a macOS reader, a Windows reader: does each path
reach a working install with the commands given; the "no separate yt-dlp"
claim: pyproject lists yt-dlp>=2024.0 as a dependency and
core/deps.get_command resolves yt-dlp via "python -m yt_dlp" when the binary is
absent (trace it). SKILL.md: tests/test_skill_license.py constrains the first
lines; confirm the edit is outside them. check-docs.py at a simulated 0.17.0:
no offenders, including the two new troubleshooting entries (no version
literals).

YOU MAY RUN: read-only commands only (cat, grep, sed -n, git log/show/diff on
the checkout, python -c for parsing). YOU MAY NOT: run pytest, builds,
installs, pip, Docker, servers, network calls, or anything that writes. Name
any check you could not run as an exact command so the lead can run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round-3 finding as FIXED / PARTLY / NOT FIXED / DECLINED-OK, one line
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
