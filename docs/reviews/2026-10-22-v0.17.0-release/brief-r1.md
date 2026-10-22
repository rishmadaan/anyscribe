You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #20 "Require Python 3.11, add Starlette and FastAPI
security floors (0.17.0 prep)", branch release/python-3.11-starlette-floor, head
commit c791f91d4db91917ccaac42c2b2630793638232a, against main ecd2899
(v0.16.5 plus the five merged audit PRs #15 to #19). Checkout to read:
<checkout> (a detached clone at that commit). The full diff
(13 files) is at <run-folder>/diff-r1.patch. The lead's own evidence
(tests, pip dry runs, PyPI facts) is at <run-folder>/lead-evidence-r1.md;
treat it as claims to check where you can.

WHY IT EXISTS (the owner's ask, in his words, 2026-10-22, answering four
decisions left open by the audit): "1. yes cut a release" ... "3. go with your
recommendation now, should do it not itself before release" (dropping Python
3.10, which the lead had recommended at the next minor) ... "4. go with your
recommendation now, should do it not itself before release" (a direct
starlette>=1.3.1 floor). The yt-dlp JavaScript runtime question (item 2) is
still open and deliberately NOT in this PR. The release itself (version bump to
0.17.0, tag, PyPI publish) happens after merge via scripts/release.sh, which
edits src/anyscribe/__init__.py and pyproject.toml; this PR must leave the
version at 0.16.5 so that script works, and must already carry the
"## 0.17.0" CHANGELOG entry that scripts/check-docs.py will demand once the
version is bumped.
FIRST QUESTION: is this the job he asked for, and the right instrument for it?
If the brief, the goal or the spec is wrong, say so instead of reviewing around it.

MUST NEVER HAPPEN: the published 0.17.0 fails to install on Python 3.11, 3.12,
3.13 or 3.14 because the pins cannot resolve together; a 3.10 user gets a
broken upgrade instead of being held on 0.16.5; a user-visible string still
says 3.10+; the installers' version checks reject a valid Python or accept an
invalid one; CI, publish.yml or check-docs.py fails on this SHA or on the
post-merge bump commit; CHANGELOG claims something the merged code does not do
(check each CHANGELOG bullet against the actual changes in PRs #15 to #19 on
main, use git log/show in the checkout); a version string "0.17.0" placed where
check-docs.py would flag it before the bump (it scans docs/user, landing,
README.md, src/anyscribe/skill).
SETTLED, DO NOT REOPEN: dropping 3.10 and adding the Starlette floor are the
owner's decisions; the yt-dlp runtime is out of scope; the repo's own docs use
em dashes, house style. Journal entries are append-only, so the 2026-10-21
audit journal's "decisions left to the owner" section is deliberately
untouched; the new journal entry records the outcome.
SOURCES: the checkout (pyproject.toml, .github/workflows/ci.yml and
publish.yml, install.sh, install.ps1, src/anyscribe/core/deps.py, README.md,
CONTRIBUTING.md, docs/user/getting-started.md, landing/index.html,
landing/docs/getting-started.html, CHANGELOG.md, BACKLOG.md,
docs/building/_index.md, docs/building/journal/2026-10-22-v0170-python-311-starlette-floor.md,
scripts/release.sh, scripts/check-docs.py, scripts/rehearse-migration.sh);
the diff; the lead evidence.

LENS (Every review): Is this the job he asked for? Use it the way he will: he
runs ./scripts/release.sh 0.17.0 after merge and the publish workflow runs.
Claims worded stronger than their evidence, in CHANGELOG, BACKLOG and the
journal especially.
LENS (Code PR): His goal written as invariants: every user-visible Python
requirement string equals 3.11+; the dependency set resolves on every CI
Python; the floors are the lowest that satisfy the stated reason (no higher
than needed, no lower than works); release.sh and check-docs.py succeed in
sequence after merge. Try to break each: install.sh resolve_python with
python3.13 present but old, python3 at 3.10, no python3.x suffix binaries;
install.ps1's version test ($major -ge 3 -and $minor -ge 11) with
"3.9", "3.11", "3.14"; deps.py's doctor check at (3, 11). Grep the checkout
for any remaining "3.10" a user can see (exclude docs/reviews, docs/superpowers,
old journal entries, ui/, .venv, node_modules). Does any dependency in
pyproject (uvicorn[standard], python-multipart, mcp>=2,<3, faster-whisper,
pystray, pyobjc) have a Python ceiling or a Starlette/FastAPI pin that
conflicts with the new floors? Is rehearse-migration.sh affected by the Python
floor? Does the CHANGELOG entry's claim "The CLI refreshes the installed copy
on its next run" match src/anyscribe/cli/main.py (the .version marker logic)?
Does "about 40" for skill and docs corrections match the audit record in
docs/reviews/2026-10-21-staleness-audit/audit/ (skill 39 findings, user docs
42)?

YOU MAY RUN: read-only commands only (cat, grep, sed -n, git log/show/diff on
the checkout, python -c for parsing). YOU MAY NOT: run pytest, builds,
installs, pip, servers, network calls, or anything that writes. Name any check
you could not run as an exact command so the lead can run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Findings, most severe first, numbered I1, I2...:
   severity (blocker / should-fix / nit, only these words); CONFIRMED (you
   reproduced or traced it) or PLAUSIBLE; where (file:line); what goes wrong,
   as a concrete scenario; the fix (exact replacement wording for docs).
3. Answers to any questions in this brief (advice, not findings).
4. Pending owner checks: things only the owner can confirm. They do not block
   the verdict.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
