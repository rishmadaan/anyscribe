You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #20 "Require Python 3.11, add Starlette and FastAPI
security floors (0.17.0 prep)", branch release/python-3.11-starlette-floor, head
commit a29d3402c494334cdc41aeff2ef39fec37f27b26 (round 3; round 1 reviewed c791f91, round 2 reviewed 6ee52d7),
against main ecd2899 (v0.16.5 plus the five merged audit PRs #15 to #19).
Checkout to read: <checkout> (a detached clone at that commit). Full diff against
main: <run-folder>/diff-r3.patch; the round-2 fix commit alone: <run-folder>/fixes-r3.patch. Lead
evidence (claims to check where you can; the Docker transcripts are primary
sources): <run-folder>/lead-evidence-r3.md. Round-2 reports: <run-folder>/report-gpt-6-astra-r2.md
(correctness) and <run-folder>/report-opus-5.5-r2.md (fit). Round-1 reports:
<run-folder>/report-gpt-6-astra-r1.md, <run-folder>/report-opus-5.5-r1.md.

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
or installs anyscribe with a Python other than the one that passed its check;
CI, publish.yml or check-docs.py fails on this SHA or after the bump;
CHANGELOG claims something the merged code does not do.
SETTLED, DO NOT REOPEN: the two owner decisions; yt-dlp out of scope; em dashes
in the repo's docs are house style; the 2026-10-21 audit journal is
append-only; the BACKLOG 0.17.0 row says "publication pending" on purpose;
Ubuntu 22.04's python3.11 package being 3.11.0rc1 is upstream's packaging, and
pip's requires-python check uses sys.version_info[:3] so it counts as 3.11.0.

PRIOR ROUNDS, round 2 findings and the builder's responses (claims; verify):
- Astra I1 (multi-word apt string reaches dnf/pacman quoted): FIXED,
  check_python picks the package per manager (apt: "python3.11
  python3.11-venv"; dnf: "python3.11"; else "python3"); the apt branch
  word-splits, the others stay quoted single names.
- Astra I2 (install.ps1 saves the name "python"; Refresh-Path can re-point it):
  FIXED, both acceptance branches store sys.executable (trimmed) and the
  final hint prints it quoted.
- Astra I3 / Opus I3 (manual Linux steps still use the old pip; Debian 11 has
  no 3.11 package): FIXED with the fit reviewer's wording: the one-line
  installer first, else "sudo apt install python3.11 python3.11-venv pipx"
  and "pipx install --python python3.11" in step 3; Debian 11 pointed to 12.
  The correctness reviewer's venv wording was not used (pipx is the simpler
  route for the reader and matches what the installer does).
- Astra I4 / Opus I4 (apt failure under set -e skips the honest die): FIXED
  with "|| true" on the install_package call; reproduced on Debian 11.
- Astra I5 (installer is not an upgrade path; pip install lacks --upgrade):
  FIXED, both installers pass --upgrade and pipx passes --force; CHANGELOG
  narrowed to pip/installer installs and describes the real upgrade path.
- Opus I1 (pipx keeps an existing venv, exit 0): FIXED with --force;
  reproduced in Docker.
- Opus I2 (quick pip routes name no Python version): FIXED in README and
  getting-started, plus a one-line warning.
- Opus I5 / Astra I6 (journal candidate list): FIXED.
- Opus I6 (try the py launcher): FIXED, both ps1 loops try python, python3, py.
- Opus I7 (CHANGELOG pipx scope and skill wording): FIXED with the given
  wording.
- Opus pre-existing note (install.ps1 "exit 1" under irm | iex may close the
  window): DECLINED-OK for this PR, pre-existing, recorded as a follow-up.
- Astra: Windows parse and real Windows run DECLINED-OK (no Windows or pwsh
  here; listed to the owner). dnf/pacman real runs: not done, disclosed.

SOURCES: the checkout (install.sh, install.ps1, pyproject.toml,
.github/workflows/ci.yml and publish.yml, src/anyscribe/core/deps.py,
src/anyscribe/cli/main.py, src/anyscribe/cli/skill_cmd.py,
src/anyscribe/core/updater.py, README.md, CONTRIBUTING.md,
docs/user/getting-started.md, landing/index.html,
landing/docs/getting-started.html, CHANGELOG.md, BACKLOG.md,
docs/building/_index.md,
docs/building/journal/2026-10-22-v0170-python-311-starlette-floor.md,
scripts/release.sh, scripts/check-docs.py); both patches; the lead evidence
and the two Docker transcripts; the four prior reports.

LENS (Every review): Is this the job he asked for? Use it the way he will:
./scripts/release.sh 0.17.0 after merge, then the publish workflow; a 3.10
user reads the CHANGELOG and follows it. Claims worded stronger than their
evidence.
LENS (Code PR, round 3): mark every round-2 finding FIXED / PARTLY / NOT FIXED
/ DECLINED-OK with one line of evidence each; then hunt for NEW defects the
round-2 fixes introduced. Concrete probes: install.sh check_python's new local
py_pkg and case: does "local" inside the if-branch parse in bash 3.2 and 5;
is LINUX_PKG set before check_python runs; what does macOS get. The pip path
now runs "pip install --upgrade": does --upgrade change anything for the git
method (pip_cmd="git+URL") or for a fresh install; does "pipx install --force"
behave on a fresh install (the Docker transcript says yes). install.ps1:
$script:PythonCmd is now a full path from sys.executable: trace every later
use (lines with PythonCmd: yt_dlp check, pip installs, sysconfig call, the
final hint) and say whether "& $script:PythonCmd" works with a path that
contains spaces (C:\Program Files\Python312\python.exe); does "(... 2>$null).Trim()"
throw when the command prints nothing; does the "py" launcher entry behave
with "py -c" and "py -m pip". Docs: read the new getting-started paragraph
(line ~302) as a reader on Ubuntu 22.04 and on Debian 12; does every command
in it exist and do what it says (pipx on 22.04 is 1.0.0; "pipx install
--python python3.11" with a bare name rather than a path). CHANGELOG Breaking
bullet: is each sentence true given install.sh, install.ps1 and
core/updater.py. check-docs.py: simulate the bump to 0.17.0 and confirm no
offenders.

YOU MAY RUN: read-only commands only (cat, grep, sed -n, git log/show/diff on
the checkout, python -c for parsing). YOU MAY NOT: run pytest, builds,
installs, pip, Docker, servers, network calls, or anything that writes. Name
any check you could not run as an exact command so the lead can run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round-2 finding as FIXED / PARTLY / NOT FIXED / DECLINED-OK, one line
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
