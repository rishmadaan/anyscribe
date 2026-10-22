You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #21 "Give yt-dlp a JavaScript runtime for YouTube
(Deno or Node), install Deno when missing (0.17.1 prep)", branch
feat/youtube-js-runtime, head commit 6cad090b6f367e70690a790cf7d489bf8b20ac17 (round 2; round 1 reviewed 0b1dffb),
against main b061832 (v0.17.0). Checkout to read: <checkout> (a detached clone at
that commit). Full diff against main: <run-folder>/diff-r2.patch; the round-1 fix commit
alone: <run-folder>/fixes-r2.patch. Lead evidence: <run-folder>/lead-evidence-r2.md. Round-1
reports: <run-folder>/report-gpt-6-astra-r1.md (correctness), <run-folder>/report-opus-5.5-r1.md (fit).

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
Instagram changes behaviour; the installers exit non-zero because of the
optional runtime step (decline, no terminal, probe failure, install failure
must all only warn); Deno's script runs interactively; a machine with Node 22+
gets Deno installed; a runtime below yt-dlp's minimum or an unrelated binary is
reported as usable; anything new on stdout for `anyscribe URL --json --quiet`
or the MCP stdio server; pip install fails to resolve yt-dlp[default] on 3.11
to 3.14; docs claim more than the code does; a version literal check-docs.py
would flag before the bump.
SETTLED, DO NOT REOPEN: option (c); accepting Node 22+ instead of forcing Deno;
runtime optional at run time (warn, do not refuse); one warning per process
(the web server's terminal, not the browser, is where it lands; a job note in
the UI is out of scope); em dashes in the repo's docs; BACKLOG 0.17.1 row says
"publication pending"; yt-dlp's 60-day auto-update is existing behaviour.

PRIOR ROUND findings and the builder's responses (claims; verify each):
- Astra I1 / Opus I2 (any deno or node accepted; identity and version
  unchecked): FIXED. deps.py _probe_js_runtime runs "<path> --version" with a
  10 s timeout, requires exit 0, requires deno's output to start with "deno ",
  parses the first x.y.z, and skips anything below JS_RUNTIME_MIN (deno 2.3,
  node 22). find_js_runtime tries deno on PATH, ~/.deno/bin/deno, then node,
  and returns (name, path, "name x.y.z"). install.sh js_runtime_found checks
  deno's banner and 2.3+, node 22+, with digit-validated parsing;
  install.ps1 the same via regex.
- Astra I2 (bash arithmetic on non-numeric output; unguarded /dev/tty read):
  FIXED. semver_major_minor + regex guards; "if ! read ... </dev/tty" skips
  with a warning and returns 0.
- Astra I3 (PowerShell failures escape to the fatal handler): FIXED, the whole
  Test-JsRuntime body is in try/catch that warns and returns.
- Astra I4 / Opus I5 (auto-update upgrades bare yt-dlp): FIXED,
  "yt-dlp[default]" plus the manual hints; test
  test_ytdlp_auto_update_keeps_the_default_extra.
- Astra I5 (node test depends on the reviewer's home): FIXED, every detection
  test patches Path.home to a tmp dir and the warning flag via monkeypatch.
- Astra I6 / Opus I6 (unzip prerequisite): FIXED in both troubleshooting files;
  install.sh's failure text says Deno's installer needs unzip or 7z.
- Astra I7 / Opus I7 (wording): FIXED ("may miss formats or fail"; journal
  describes what doctor actually shows; landing "Node 22+"; header step 3;
  CHANGELOG mentions the unzip/sudo step; shorter warning).
- Opus I1 (warning on stdout breaks --json and MCP): FIXED, err_console =
  Console(stderr=True) for the runtime warning and for the yt-dlp auto-update
  chatter; test asserts stdout == "" and the text on stderr.
- Opus I3 (doctor's missing row has no link): FIXED, the description carries
  the Deno install URL.
- Opus I4 (pip-route and doctor docs): FIXED in getting-started:33 and :72,
  commands.md doctor list, README:41 and :53; HTML regenerated.
- Opus I8 (/api/health ok flips on the optional row): FIXED, ok considers
  required rows only.
- Opus I9 (installer tests for Node-22 and decline paths): FIXED, three tests
  under a pseudo-terminal (lead evidence).
- Opus answer (cli/download.py _download_video also calls yt-dlp): the video
  download path now passes the same flag and warns for YouTube; Instagram
  video downloads get the flag too (harmless: yt-dlp ignores runtimes it does
  not need) but no warning.
- Lead's own find: Ubuntu 24.04 with no python3 died asking apt for
  python3.11; check_python now installs the distro's python3 first and only
  then python3.11 by name (apt) or python3.11 (dnf).
- DECLINED-OK: Windows runs (no Windows or pwsh here); a web-UI job note for
  the missing runtime (out of scope); the Opus round-1 pending owner checks go
  to the owner.

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
scripts/check-docs.py); both patches; the lead evidence; the round-1 reports.

LENS (Every review): Is this the job he asked for? Use it the way he will: the
one-line installer on a Linux box with Node 24 and no Deno; a fresh Mac or
Ubuntu with neither; a pip-only user running doctor and a YouTube
transcription through Claude Code (--json --quiet). Claims worded stronger
than their evidence.
LENS (Code PR, round 2): mark every round-1 finding FIXED / PARTLY / NOT FIXED
/ DECLINED-OK with one line of evidence each; then hunt for NEW defects the
fixes introduced. Concrete probes: _probe_js_runtime on "deno 2.9.7 (stable,
release, aarch64-apple-darwin)" and on "v26.9.0" and on node printing a
warning line before the version; a deno that hangs (timeout) and one that
prints to stderr; the regex picking up a date-like number before the version;
find_js_runtime returning the ~/.deno copy when PATH deno is too old (desired);
js_runtime_args with the Windows path "C:\Program Files\..." (colon split
in yt-dlp); the single-lookup refactor: do youtube.py and download.py both
warn only for YouTube and never twice per process; err_console vs the
--json path in cli/transcribe.py and the MCP server (is stderr also captured
anywhere and surfaced as an error?); health.py "ok" with the optional row
missing and with a required row missing; install.sh: js_runtime_found under
set -euo pipefail when "deno --version" exits non-zero (the || true inside
$(...)), semver_major_minor on "v24.22.0" and on "" ; the guarded read when
/dev/tty exists but EOF arrives; check_js_runtime on macOS without brew (falls
to the curl branch: is that right for a Mac without Homebrew?); the unzip
pre-install only on apt (dnf/pacman users without unzip get Deno's own error,
then the warn); check_python's two-step package attempt on Ubuntu 22.04 (first
"python3 python3-venv" is a no-op, then python3.11) and on Debian 12; the
tests: can each new test fail for the right reason; is the script(1) harness
portable to the CI runner (ubuntu-latest has script from bsdutils); does the
pseudo-terminal test leak if script hangs (timeout=60). Docs: is every
sentence of the CHANGELOG 0.17.1 entry true of the code now.

YOU MAY RUN: read-only commands only (cat, grep, sed -n, git log/show/diff on
the checkout, python -c for parsing). YOU MAY NOT: run pytest, builds,
installs, pip, yt-dlp, Docker, servers, network calls, or anything that
writes. Name any check you could not run as an exact command so the lead can
run it.

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
