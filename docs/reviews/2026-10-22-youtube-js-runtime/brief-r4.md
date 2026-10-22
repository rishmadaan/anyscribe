You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #21 "Give yt-dlp a JavaScript runtime for YouTube
(Deno or Node), install Deno when missing (0.17.1 prep)", branch
feat/youtube-js-runtime, head commit ec59f544259fb024b47d0ab7eeef8e43876d3031 (round 4, the last round under the
cap; rounds 1 to 3 reviewed 0b1dffb, 6cad090, af41426), against main b061832
(v0.17.0). Checkout to read: <checkout> (a detached clone at that commit). Full
diff against main: <run-folder>/diff-r4.patch; the round-3 fix commits alone (3e6c883
and ec59f544259fb024b47d0ab7eeef8e43876d3031): <run-folder>/fixes-r4.patch. Lead evidence with two pinned Docker transcripts:
<run-folder>/lead-evidence-r4.md. Round-3 reports: <run-folder>/report-gpt-6-astra-r3.md
(correctness), <run-folder>/report-opus-5.5-r3.md (fit). Earlier: r1 and r2 reports in
<run-folder> (astra r1, sol r2, opus r1, r2).

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
optional runtime step; Deno's script runs interactively; a machine with Node
22+ gets Deno installed; a runtime below yt-dlp's minimum, a failing program
or an unrelated binary is reported as usable; a failed winget or an old deno
reported as "installed"; anything new on stdout for `--json --quiet` or the
MCP stdio server; pip install fails to resolve yt-dlp[default] on 3.11 to
3.14; docs claim more than the code does; a version literal check-docs.py
would flag before the bump.
SETTLED, DO NOT REOPEN: option (c); accepting Node 22+ instead of forcing Deno;
runtime optional at run time; one warning per process; em dashes in the
repo's docs; BACKLOG 0.17.1 row says "publication pending"; the 60-day
auto-update exists; pseudo-terminal tests take about 30 s; no Windows or
PowerShell here; macOS without timeout(1)/gtimeout probes unbounded; deno
release candidates (2.3.0-rc.1) are accepted as 2.3; the review record's
absolute paths are scrubbed by the lead at commit time (the same scrub as the
two earlier records on main).

PRIOR ROUND (round 3) findings and the builder's responses (claims; verify):
- Astra I1 (bash timeout only SIGTERMs): FIXED, `timeout --kill-after=1 10`
  and the gtimeout twin; the comment says "about 11 s".
- Astra I2 (ps1 drains stdout only; .Result unbounded): FIXED, Get-ProbeLines
  starts ReadToEndAsync on both streams, WaitForExit(10000), then
  Task.WaitAll(@(out, err), 5000) before reading .Result.
- Astra I3 (installers read one stdout line; "deno 2.3." accepted): FIXED,
  probe_version returns stdout+stderr on exit 0 and version_banner scans every
  line with anchored regexes (deno needs X.Y.Z plus a non-digit boundary);
  ps1 Get-RuntimeBanner does the same over all lines. Lead ran the six bash
  cases (lead evidence).
- Astra I4 (ps1 "deno installed" without checking winget or the version):
  FIXED, requires winget exit 0 and Test-DenoUsable on the re-probed deno.
- Astra I5 (pinned transcript empty): FIXED, two pinned transcripts now, for
  af41426 and for this SHA; both print the installer hash on line 2.
- Astra I6 (README pip sentence; CHANGELOG "installs unzip"): FIXED with the
  given wording.
- Opus I1 (CHANGELOG lacks the upgrade instruction): FIXED, new bullet.
- Opus I2 (absolute paths in the record): applied at commit time (settled).
- Opus I3 (commands.md overclaims stderr; Windows PATH notice): FIXED, the
  exception is named in both places.
- Opus I4 (README yt-dlp; Windows appendix bare yt-dlp line): FIXED.
- Opus I5 (skill hands sudo/remote script to Claude's shell; installer
  description): FIXED, the skill tells Claude to hand those commands to the
  user, and SKILL.md's installer line names ffmpeg and the runtime.
- Opus I6 (no test of cli/download.py): FIXED,
  test_video_download_flags_youtube_only (Instagram argv equals the
  pre-PR command; YouTube carries the flag); mutation: dropping the platform
  check fails it.
- Opus I7 (Linux python wording): FIXED in CHANGELOG and journal.
- Opus I8 (BACKLOG 0.17.0 "(current)"): FIXED.
- Opus I9 (ps1 stderr drain; node pre-release banners; deps install_pip bare):
  FIXED, all three (bash and ps1 node regexes allow a "-suffix").
- Opus I10 (Deno prompt does not say the script edits the profile): FIXED, a
  line before the prompt on the non-Homebrew branch.
- DECLINED-OK: Windows runs; dnf/pacman real runs; a challenge-requiring
  YouTube video; the probe-timeout branch untested (tests stub `command`).

SOURCES: the checkout (pyproject.toml, src/anyscribe/core/deps.py,
src/anyscribe/downloaders/youtube.py, src/anyscribe/downloaders/instagram.py,
src/anyscribe/cli/download.py, src/anyscribe/cli/main.py (doctor and
_check_path_windows), src/anyscribe/web/routes/health.py, install.sh,
install.ps1, tests/test_js_runtime.py, tests/test_install_sh.py,
tests/test_youtube_downloader.py, README.md, docs/user/getting-started.md,
docs/user/troubleshooting.md, docs/user/commands.md, src/anyscribe/skill/SKILL.md,
src/anyscribe/skill/references/troubleshooting.md, docs/building/downloaders.md,
landing/index.html, CHANGELOG.md, BACKLOG.md, docs/building/_index.md,
docs/building/journal/2026-10-22-v0171-youtube-js-runtime.md,
scripts/check-docs.py); both patches; the lead evidence and both pinned Docker
transcripts; the prior reports.

LENS (Every review): Is this the job he asked for? Use it the way he will: the
one-line installer on a Linux box with Node 24 and no Deno; a fresh Mac or
Ubuntu with neither; a pip-only user running doctor and a YouTube
transcription through Claude Code (--json --quiet). Claims worded stronger
than their evidence.
LENS (Code PR, round 4): mark every round-3 finding FIXED / PARTLY / NOT FIXED
/ DECLINED-OK with one line of evidence each; then hunt for NEW defects the
fixes introduced. Concrete probes: version_banner's `read -r` loop under
set -euo pipefail when the input is empty (probe failed): does the pipeline
"probe_version ... | version_banner deno || true" leave v empty and continue;
pipefail with probe_version returning 1 into version_banner; the
"[[ ... =~ ]]" lines that now run without an if (a non-match returns 1: can
that trip errexit inside js_runtime_found when called as "js_runtime_found &&
return 0"); BASH_REMATCH after the bare match; the deno boundary regex on
"deno 2.3.0 (stable" and on "deno 2.3.0rc1"; Get-ProbeLines when WaitAll
times out but the process exited 0 (returns null: is a null-returning probe
treated as "could not be read", never as a crash); Test-DenoUsable's output
when deno is absent after winget; the kill-after flag on BusyBox or old
coreutils (does "timeout --kill-after=1 10" parse on Ubuntu 22.04, Debian 11,
Alpine); tests: does test_node_that_fails_its_probe_is_not_accepted still
exercise the new code path; is anything in the three installer helpers
unreachable. Docs: CHANGELOG 0.17.1 sentence by sentence; the skill's new
sentence about handing sudo commands to the user; the two Docker transcripts
against the claims in lead evidence (installer hash line, doctor row, the
--json result).

YOU MAY RUN: read-only commands only (cat, grep, sed -n, git log/show/diff on
the checkout, python -c for parsing). YOU MAY NOT: run pytest, builds,
installs, pip, yt-dlp, Docker, servers, network calls, or anything that
writes. Name any check you could not run as an exact command so the lead can
run it.

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
