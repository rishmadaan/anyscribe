You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #16 (Installers, CI and dependency pins), branch `audit/infra`, head commit
52ef77ff8a585f90864409d5375372eaa8557b29, against main b3cddc1 (v0.16.5). Checkout to read: <checkout> (a git
worktree of <repo> at that commit). The full diff is
saved at <run-folder>/reviews/infra/diff-r2.patch. The audit findings this PR implements are at <run-folder>/audit/infra.md.
The implementer's own report is at <run-folder>/reviews/impl-infra.md (treat its claims as claims).

WHY IT EXISTS (the owner's ask, in his words): "Do an end-to-end audit of what
all is out of date and should be updated. Logically file the PRs. Run
independent review on those PRs. If they are good to go, merge them."
FIRST QUESTION: is this the job he asked for, and the right instrument for it?
If the brief, the goal or the spec is wrong, say so instead of reviewing around it.

MUST NEVER HAPPEN: a doc or skill file that tells a user or an agent to run a
command the code rejects; a doc that claims more than the code does; a change
that breaks CI (lint, tests, docs render check, static bundle check) or a user's
install; anything deleted that should not be; behaviour changes smuggled into a
docs PR.
SETTLED, DO NOT REOPEN: yt-dlp's JavaScript-runtime requirement (Deno) and
dropping Python 3.10 are decisions left to the owner, deliberately out of scope.
CHANGELOG.md gets its entries at release time, not in these PRs. The repo's own
docs use em dashes; that is house style, not a defect.
SOURCES: the checkout above (code is the source of truth: src/anyscribe/cli/*.py,
providers/*.py, core/*.py, web/routes/*.py, config/settings.py, scripts/*.py,
.github/workflows/*.yml); the diff; the spec; CHANGELOG.md and BACKLOG.md for
history.

LENS (Every review): Is this the job he asked for? Use it the way he will: a
user reads the doc and types the command, or Claude Code reads the skill and
runs it; which copy does his machine load (the bundled skill under
src/anyscribe/skill is what `anyscribe install-skill` copies to
~/.claude/skills/anyscribe). Claims worded stronger than their evidence.
LENS (Code PR): His goal written as invariants: every documented command, flag,
default, path, JSON field and route must match the code at this commit. Try to
break each fix with concrete inputs: for each changed command example, trace it
through the Typer app in cli/main.py and the subcommand module and say whether
it parses. Tests that cannot fail. The same pattern elsewhere: any other doc
line with the same bug the PR fixed but did not touch. Docs and spec that claim
more than the code does; spec that was wrong and got built anyway. CI on this
exact SHA: a merge verdict is conditional on it.
LENS (this PR, installers and CI): read install.sh top to bottom as a fresh macOS and a fresh Linux user; does every branch (pipx present, pipx absent, python3 missing, ffmpeg missing) still reach a working `anyscribe`? Does the new sysconfig PATH hint work on Python 3.10 (get_preferred_scheme) and inside pipx or a venv where the user scheme is irrelevant? Is any `scribe` left where it should still say scribe (alias text) or any `anyscribe` where it breaks a box border? install.ps1: do the edited strings still parse as PowerShell (quotes, backticks, here-strings)? Workflows: are checkout@v7, setup-python@v7, setup-node@v7 real tags with compatible inputs (cache, cache-dependency-path); does publish.yml's new check-docs step run before anything irreversible; is the Python 3.14 matrix leg likely to pass with these pins (ctranslate2 is not installed in CI, confirm). pyproject: do the beaupy cap and the python-multipart floor conflict with any other pin; is the comment wording accurate to beaupy 4.0.1's actual change.

YOU MAY RUN: read-only commands only (cat, grep, sed -n, git log/show/diff on
the checkout, python -c for parsing). YOU MAY NOT: run pytest, builds,
installs, servers, network calls, or anything that writes. Name any check you
could not run as an exact command so the lead can run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Round 2+: every earlier finding as FIXED / PARTLY / NOT FIXED / DECLINED-OK,
   one line of evidence each; then NEW defects the fixes introduced.
3. Findings, most severe first, numbered I1, I2...:
   severity (blocker / should-fix / nit, only these words); CONFIRMED (you
   reproduced or traced it) or PLAUSIBLE; where (file:line); what goes wrong,
   as a concrete scenario; the fix (exact replacement wording for docs).
4. Answers to any questions in this brief (advice, not findings).
5. Pending owner checks: things only the owner can confirm. They do not block
   the verdict.
6. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.

PRIOR ROUNDS. Round 1 reviewed 981a7eb. The fix commit is 52ef77f (installer and publish.yml changes only). The builder's claimed evidence is in <run-folder>/reviews/impl-infra-r2.md; treat it as a claim to check.
- Astra I1 / Opus I2 (pipx route post-install launch): claimed FIXED. run_post_install now returns unless --ui/--onboard; picks `anyscribe` on PATH, else (USED_PIPX) the pipx bin dir's anyscribe checked with -x (warns and skips with rc 0 if missing), else "$PY" -m anyscribe; command held in a bash array.
- Astra I2 (Python without pip never reaches pipx): claimed FIXED. New first branch `if ! "$PY" -m pip --version`; pipx install code moved unchanged into a helper install_with_pipx used by both branches; builder tested with a --without-pip venv (old script: "No module named pip ... pip install failed"; new: "has no pip. Using pipx instead").
- Astra I3 (PATH hint assumes user scheme): claimed FIXED. python -c snippet tries sysconfig default scripts dir then user scheme dir, prints the first containing an executable anyscribe; else prints "Run it with: $PY -m anyscribe --version".
- Astra I4 (publish still skips docs render and migration rehearsal): claimed FIXED. Three steps added after the drift gate and before Build package: Render docs; Committed HTML matches sources; Rehearse migration.
- Opus I1 (building docs not updated for the new publish gates, beaupy cap, 3.14): routed to PR #19 (building-docs), which is being fixed in parallel; DECLINED for this PR with that reason.
- Opus I3 / Astra box widths: claimed FIXED; builder re-measured every box line at 39 columns (install.sh 117-120, 409-414, 416-424; install.ps1 22-25, 211-219).
- Builder also noted (not fixed, pre-existing): if Python has no pip, pipx is absent and the package manager is unknown, the last fallback `"$PY" -m pip install --user pipx` fails under set -e without a friendly message.

Check that each fix is real (read the code, probe it, try to break it with concrete inputs), and look for anything new, especially problems the fixes introduced. Concrete inputs to try: a pipx bin dir with a space; USED_PIPX true but the binary missing; a venv without pip; Python 3.10 for the sysconfig snippet; the PATH hint when anyscribe is in the default scheme dir but not the user dir and vice versa.
