You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #21 "Give yt-dlp a JavaScript runtime for YouTube
(Deno or Node), install Deno when missing (0.17.1 prep)", branch
feat/youtube-js-runtime, head commit 0b1dffb909f1e3feb3e2db5f812ff750aa85528c, against main b061832 (v0.17.0).
Checkout to read: <checkout> (a detached clone at that commit). Full diff:
<run-folder>/diff-r1.patch. Lead evidence (claims to check where you can; the live
yt-dlp runs and PyPI facts are the lead's): <run-folder>/lead-evidence-r1.md.

WHY IT EXISTS (the owner's ask, in his words, 2026-10-22). After the lead laid
out three options for yt-dlp's JavaScript-runtime requirement, (a) document,
(b) yt-dlp[default] plus a doctor warning, (c) also install a runtime, he
said: "I'd go with reliable and stabel functionaility over a shortcut, so by
that fundamental c will e a better choice?" and then "yes, let's go with C."
The approved scope, in the lead's words he said yes to: switch the dependency
to yt-dlp[default]; have the installers install Deno when neither Deno 2.3+
nor Node 22+ is present; if Node is present, pass it to yt-dlp instead; add a
"JavaScript runtime" row to anyscribe doctor and a one-line warning before a
YouTube download when none is found; ship as 0.17.1 after review. pip-only
users get the warning and hint, not an automatic install. He also asked that
after shipping, the lead update his Mac (an editable git install of this
repo) and his Linux box (nothing installed yet; it has Node 24) and watch the
live update.
FIRST QUESTION: is this the job he asked for, and the right instrument for it?
If the brief, the goal or the spec is wrong, say so instead of reviewing around it.

MUST NEVER HAPPEN: a YouTube download that worked before this PR now fails
(for example because --js-runtimes is passed with a bad value, or a runtime
below yt-dlp's minimum is named and yt-dlp errors instead of warning); the
Instagram downloader changes behaviour; the installers fail or exit when the
runtime step fails (it is optional: decline or failure must only warn);
Deno's install script runs interactively or edits the wrong profile; a
machine with Node 22+ gets Deno installed anyway; pip install of 0.17.1 fails
to resolve yt-dlp[default] on Python 3.11 to 3.14; CHANGELOG, README or
troubleshooting claim more than the code does; a version string "0.17.1"
placed where scripts/check-docs.py would flag it before the bump (docs/user,
landing, README.md, src/anyscribe/skill); a "0.16.x" or "0.17.0" literal
without the version-pin-ok marker in those folders.
SETTLED, DO NOT REOPEN: option (c) itself; accepting Node 22+ instead of
forcing Deno; the runtime being optional at runtime (warn, do not refuse);
em dashes in the repo's docs are house style; the BACKLOG 0.17.1 row says
"publication pending" on purpose; yt-dlp's 60-day auto-update is existing
behaviour.
SOURCES: the checkout (pyproject.toml, src/anyscribe/core/deps.py,
src/anyscribe/downloaders/youtube.py, src/anyscribe/downloaders/instagram.py,
src/anyscribe/cli/main.py (doctor), install.sh, install.ps1,
tests/test_js_runtime.py, tests/test_install_sh.py,
tests/test_youtube_downloader.py, README.md, docs/user/getting-started.md,
docs/user/troubleshooting.md, src/anyscribe/skill/references/troubleshooting.md,
docs/building/downloaders.md, landing/index.html, CHANGELOG.md, BACKLOG.md,
docs/building/_index.md,
docs/building/journal/2026-10-22-v0171-youtube-js-runtime.md,
scripts/check-docs.py); the diff; the lead evidence.

LENS (Every review): Is this the job he asked for? Use it the way he will: he
runs the one-line installer on a Linux box with Node 24 and no Deno; a user
without either runs it on a fresh Mac or Ubuntu; a pip-only user runs
anyscribe doctor and a YouTube transcription. Claims worded stronger than
their evidence.
LENS (Code PR): His goal written as invariants: every YouTube yt-dlp call
carries a runtime flag whenever a runtime exists; the flag names a binary that
exists; no runtime means one warning and an unchanged command; the installers
never exit non-zero because of this step; Node 22+ present means no Deno
install. Try to break each with concrete inputs: deno on PATH but it is a
different "deno" (a shell alias cannot be found by shutil.which, but a
same-named unrelated binary can); node 18 on PATH and no deno (the code names
node:<path> without checking the version; what does yt-dlp do with a too-old
node, warn or fail?); Windows paths with spaces inside "--js-runtimes
deno:C:\Program Files\...\deno.exe" (does yt-dlp split on the first colon
only?); ~/.deno/bin/deno present but not executable; find_js_runtime called
twice per download (once in warn, once in args) and the doctor row; the
global _js_runtime_warned under the web UI's long-lived process (one warning
per server lifetime, is that acceptable or should it be per job?); the
doctor's check_and_install loop (does an optional missing runtime get offered
for install, and what does get_install_command return for it on Linux with
install_apt=""); install.sh js_runtime_found under set -euo pipefail when
deno --version fails or node --version prints nothing; the "major" arithmetic
with a non-numeric string; the unzip pre-install; Deno's script with --yes
run from a non-interactive installer (curl | bash) and whether its
shell-setup step still prompts; install.ps1 Test-JsRuntime parse and the
[int] cast; tests: can each test fail for the right reason, and is
test_doctor_row_names_the_runtime asserting identity (the row's version and
path) rather than a count. Docs: is "YouTube downloads may miss formats or
fail" what yt-dlp actually does without a runtime (the lead observed only a
warning plus a successful download on a 19 s video); is the Linux manual
instruction's unzip requirement right; does the CHANGELOG match the code.

YOU MAY RUN: read-only commands only (cat, grep, sed -n, git log/show/diff on
the checkout, python -c for parsing). YOU MAY NOT: run pytest, builds,
installs, pip, yt-dlp, Docker, servers, network calls, or anything that
writes. Name any check you could not run as an exact command so the lead can
run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Findings, most severe first, numbered I1, I2...: severity (blocker /
   should-fix / nit, only these words); CONFIRMED (you reproduced or traced
   it) or PLAUSIBLE; where (file:line); what goes wrong, as a concrete
   scenario; the fix (exact replacement wording for docs).
3. Answers to any questions in this brief (advice, not findings).
4. Pending owner checks: things only the owner can confirm. They do not block
   the verdict.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
