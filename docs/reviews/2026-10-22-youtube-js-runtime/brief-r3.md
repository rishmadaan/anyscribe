You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #21 "Give yt-dlp a JavaScript runtime for YouTube
(Deno or Node), install Deno when missing (0.17.1 prep)", branch
feat/youtube-js-runtime, head commit af41426146c8cf833fb28d1b89df25ff926dc210 (round 3; rounds 1 and 2 reviewed
0b1dffb and 6cad090), against main b061832 (v0.17.0). Checkout to read:
<checkout> (a detached clone at that commit). Full diff against main:
<run-folder>/diff-r3.patch; the round-2 fix commit alone: <run-folder>/fixes-r3.patch. Lead
evidence: <run-folder>/lead-evidence-r3.md. Round-2 reports: <run-folder>/report-gpt-6.1-sol-r2.md
(correctness; the usual correctness model was at capacity) and
<run-folder>/report-opus-5.5-r2.md (fit). Round 1: <run-folder>/report-gpt-6-astra-r1.md,
<run-folder>/report-opus-5.5-r1.md.

WHY IT EXISTS (the owner's ask, in his words, 2026-10-22): after three options
for yt-dlp's JavaScript-runtime requirement, (a) document, (b) yt-dlp[default]
plus a doctor warning, (c) also install a runtime, he said "I'd go with
reliable and stabel functionaility over a shortcut, so by that fundamental c
will e a better choice?" and then "yes, let's go with C." Approved scope:
switch the dependency to yt-dlp[default]; installers install Deno when neither
Deno 2.3+ nor Node 22+ is present; if Node is present, pass it to yt-dlp
instead; a "JavaScript runtime" row in anyscribe doctor and a one-line warning
before a YouTube download when none is found; pip-only users get the warning
and hint, not an automatic install; ship as 0.17.1 after review.
FIRST QUESTION: is this the job he asked for, and the right instrument for it?
If the brief, the goal or the spec is wrong, say so instead of reviewing around it.

MUST NEVER HAPPEN: a YouTube download that worked before this PR now fails;
Instagram changes behaviour (its yt-dlp command must be byte-identical to
main's); the installers exit non-zero because of the optional runtime step;
Deno's script runs interactively; a machine with Node 22+ gets Deno installed;
a runtime below yt-dlp's minimum, a failing program or an unrelated binary is
reported as usable; anything new on stdout for `anyscribe URL --json --quiet`
or the MCP stdio server; pip install fails to resolve yt-dlp[default] on 3.11
to 3.14; docs claim more than the code does; a version literal check-docs.py
would flag before the bump.
SETTLED, DO NOT REOPEN: option (c); accepting Node 22+ instead of forcing Deno;
runtime optional at run time; one warning per process; em dashes in the
repo's docs; BACKLOG 0.17.1 row says "publication pending"; yt-dlp's 60-day
auto-update exists; the pseudo-terminal tests take about 25 s; no Windows
machine or PowerShell here; macOS without timeout(1) or gtimeout runs the
installer's probes unbounded (disclosed).

PRIOR ROUND (round 2) findings and the builder's responses (claims; verify):
- Sol I1 (node accepts any x.y.z; installers ignore probe exit status): FIXED.
  deps.py _JS_VERSION_LINE requires a line matching "^deno (\d+)\.(\d+)\.(\d+)\b"
  or "^v(\d+)\.(\d+)\.(\d+)$"; install.sh probe_version returns nothing when
  the program exits non-zero and js_runtime_found matches the banners by
  regex (BASH_REMATCH); install.ps1 Get-VersionLine checks ExitCode and the
  regexes are anchored.
- Sol I2 (unbounded installer probes): FIXED. probe_version uses timeout(1)
  or gtimeout when present (10 s); install.ps1 WaitForExit(10000) then Kill.
- Sol I3 (UnicodeDecodeError escapes; Instagram probed): FIXED.
  errors="replace" on the probe; download.py looks up the runtime only when
  platform == "youtube" (also Opus I1).
- Sol I4 / Opus I2 (apt package names reach dnf/pacman): FIXED, per-manager
  case for both attempts; test asserts the exact arguments per manager.
- Sol I5 / Opus I3 (three bare yt-dlp hints): FIXED, all say "yt-dlp[default]".
- Sol I6 (Docker transcript's installer hash differed; moving branch): FIXED
  in method: the round-3 run mounts the reviewed checkout and pins the package
  source to this SHA; the log prints the hash. Result in flight.
- Sol I7 (commands.md claims yt-dlp updates contaminate JSON; pip users must
  install yt-dlp; CHANGELOG apt wording): FIXED with the given wording.
- Opus I4 (journal, BACKLOG, downloaders, CHANGELOG lag): FIXED.
- Opus I5 (winget two packages in one call; mixed-OS block): FIXED.
- DECLINED-OK: Windows runs; pseudo-terminal process-group cleanup on a hang
  (timeout=60 kills the outer bash only; CI teardown cleans up).

SOURCES: the checkout (pyproject.toml, src/anyscribe/core/deps.py,
src/anyscribe/downloaders/youtube.py, src/anyscribe/downloaders/instagram.py,
src/anyscribe/cli/download.py, src/anyscribe/cli/main.py (doctor),
src/anyscribe/web/routes/health.py, install.sh, install.ps1,
tests/test_js_runtime.py, tests/test_install_sh.py,
tests/test_youtube_downloader.py, README.md, docs/user/getting-started.md,
docs/user/troubleshooting.md, docs/user/commands.md,
src/anyscribe/skill/references/troubleshooting.md, docs/building/downloaders.md,
landing/index.html, CHANGELOG.md, BACKLOG.md, docs/building/_index.md,
docs/building/journal/2026-10-22-v0171-youtube-js-runtime.md,
scripts/check-docs.py); both patches; the lead evidence; the prior reports.

LENS (Every review): Is this the job he asked for? Use it the way he will: the
one-line installer on a Linux box with Node 24 and no Deno; a fresh Mac or
Ubuntu with neither; a pip-only user running doctor and a YouTube
transcription through Claude Code (--json --quiet). Claims worded stronger
than their evidence.
LENS (Code PR, round 3): mark every round-2 finding FIXED / PARTLY / NOT FIXED
/ DECLINED-OK with one line of evidence each; then hunt for NEW defects the
fixes introduced. Concrete probes: _JS_VERSION_LINE against "deno 2.9.8
(stable, release, aarch64-unknown-linux-gnu)", "v26.9.0", "v26.9.0\r" (CRLF
on Windows: does .strip() handle it), "deno 2.3.0-rc.1", node printing
"v24.22.0" on stderr; probe_version's "|| return 1" inside an assignment
under set -e within the $(...) of the caller; BASH_REMATCH scoping after
the "||" list; "command -v timeout" on macOS (absent) vs Linux; the for loop's
first element when "command -v deno" prints nothing (an empty string: is it
skipped by the -n test); Get-VersionLine with a program that writes a lot to
stderr (the StandardError stream is redirected but never read: can the child
block on a full pipe before exit, and what does WaitForExit do then);
download.py's runtime=None default for Instagram producing exactly main's
command (compare argument lists); tests: does
test_check_python_asks_each_package_manager_by_its_own_names pass for the
right reason (install_package stub records $3) and could it pass if
check_python regressed; the pseudo-terminal tests' total runtime. Docs: read
CHANGELOG 0.17.1 sentence by sentence against the code.

YOU MAY RUN: read-only commands only (cat, grep, sed -n, git log/show/diff on
the checkout, python -c for parsing). YOU MAY NOT: run pytest, builds,
installs, pip, yt-dlp, Docker, servers, network calls, or anything that
writes. Name any check you could not run as an exact command so the lead can
run it.

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
