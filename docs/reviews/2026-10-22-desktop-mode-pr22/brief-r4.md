You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: <repo>/tests, <repo>/.venv,
<repo>/ui/node_modules. Skip any repo startup
routine; read only what this brief names (and files they point you to).

ROUND 4, the last round allowed (cap), of a size-L PR merge review. Round 3
(closing) said NOT YET on a short list; the fix is small (4 commits). Check that
each round-3 fix is real (read the code, probe it, try to break it with concrete
inputs), and look for anything new, especially problems the fixes introduced.
Say GOOD TO GO only if you would merge it yourself; otherwise NOT YET with the
exact remaining defects.

WHAT: repo <repo>, branch feat/desktop-mode at commit
0382449 (full: `git -C <repo> rev-parse HEAD`). Round 3
reviewed 240766b; the round-3 fix wave is `git diff 240766b..0382449` (4 commits).
The whole change is `git diff main...0382449`. PR #22 (draft):
https://github.com/rishmadaan/anyscribe/pull/22. Everything in this checkout is
frozen. (A separate stranger test is running on a Linux machine from a clone of
this branch; it does not touch this checkout.)

WHY IT EXISTS (the owner's ask, in his words): "AnyScribe currently runs by
opening the terminal. Is there a way that we can run it without opening the
terminal, possibly with a web app, just like how Lantern runs? We will also
have to set up a background service that runs with that web app." Then:
"realistically, if a user has to know all of this in order to use it, it is
never going to be used." Then: "I don't want to pay anything right now ... I'm
okay with shipping with the 'open anyway' thing." And: "two different install
methods: one that ships through pip, which is just the CLI version; a desktop
mode that also ships through that ... Also, I'm worried about the fact that if
we don't open the app and Claude wants to call it, how will that work?"

FIRST QUESTION: is this the job he asked for, and the right instrument for it?

MUST NEVER HAPPEN:
- A user has to know about a server, a tray, a login item or a PATH to use it.
- A login-started anyscribe that cannot find ffmpeg or Deno.
- Two trays, a stray unowned server, or a relaunch loop.
- The dashboard opens onto, attaches to, or shuts down a program that is not
  anyscribe; anyscribe signals a process that is not its own.
- A harmless-looking command kills the dashboard the user is looking at.
- Anything under ~/anyscribe/, config.yaml or .env touched by install/uninstall.
- Claude Code or the MCP server needing the desktop app to be running.
- Money, signing, or a new runtime dependency.
- A doc, help text or skill file that claims more than the code does.

SETTLED, DO NOT REOPEN: everything listed in brief-r3.md (same folder), plus:
- Process identity uses the command line (Linux: /proc/<pid>/cmdline; other
  POSIX: `ps -ww -o command=`; Windows: Win32_Process CommandLine) with the
  role token; no creation-time check (accepted).
- F5 (regex matches anywhere on the line): left as is (a pidfile is written by
  a tray; the case is unrealistic).

PRIOR ROUND (round-3 findings, the response, builder evidence to be checked):
- F1 (blocker; Linux `ps -o command=` truncated at 80 columns without a tty, so
  a long venv path could hide a real tray): FIXED. `core/tray.py` reads
  `/proc/<pid>/cmdline` on Linux (NUL → space; OSError → False); other POSIX
  uses `ps -ww`; Windows unchanged. Tests: a unit test for the Linux branch with
  a >80-char NUL-separated line ending `/x/bin/scribe\0tray\0--port\08457`
  (mutation: /proc branch disabled → fails); the real-child alias test kept as is.
  Builder note: `-ww` could not be made to fail on macOS (BSD ps never truncated
  a 397-char line, with or without COLUMNS=80); the /proc branch is what fixes
  Linux. Lead evidence: CI run 39815726235 on 0382449 (result attached at relay;
  python 3.11 failed exactly this test on 240766b).
- F2 / W/F8 (blocker; Windows ran the posix param): FIXED.
  `pytest.param("posix", marks=skipif(sys.platform == "win32"))`, `signal.SIGUSR1`
  restored in the expectation. Lead evidence: CI windows-latest on 0382449.
- F3 (should-fix; port check gated on a live tray): FIXED. `open_dashboard`
  computes `installed_port()` unconditionally and raises `PortMismatch` before
  any signal/stop/spawn; `open_cmd` defaults `port` to the installed port when
  `--port` is absent (new test `test_open_without_port_uses_the_login_item_port`);
  `test_open_other_port_refuses_even_with_no_tray` (mutation: re-gated → fails);
  docs say "while desktop mode is installed on one port". Lead evidence on this
  Mac: tray quit (no pidfile, launchd `- 0`), `desktop open --port 9000` → exit 1
  in 0 s with the message, zero anyscribe processes afterwards; plain `desktop
  open` → exit 0 in 2 s, tray back under launchd (pid in `launchctl list`),
  health app=anyscribe.
- F4 / F6 (doc nits): FIXED as appended, dated notes in the journal (append-only)
  and one clause in architecture.md about `stop_tray` and server.pid.

SOURCES (absolute paths; read, run nothing that writes):
- <run folder>/brief-r3.md (the settled
  list and the round-2 ledger), and the round-3 reports:
  <repo>/docs/reviews/2026-10-22-desktop-mode-pr22/report-gpt-6-astra-r3.md
  and .../report-fable-r3.md
- Builder report: <repo>/.superpowers/sdd/2026-10-22-desktop-mode/review-fix-r3-report.md
- Code: src/anyscribe/core/{desktop,tray}.py, src/anyscribe/cli/desktop_cmd.py
  (the round-3 diff touches these), plus any file you need to judge them.
- Tests (read only): tests/test_desktop.py, tests/test_tray.py.
- Docs touched: docs/user/commands.md, src/anyscribe/skill/references/commands.md,
  docs/building/architecture.md, docs/building/journal/2026-10-22-desktop-mode.md.

LENS:
Every review: is this the job he asked for; use it the way he will (an
editable pip install of this branch; `anyscribe` on PATH); claims worded
stronger than their evidence.
Code PR, cap round: for each FIXED item, read the code and try to break it with:
a /proc/<pid>/cmdline that is empty (zombie) or unreadable (another user's
process); a pid that exits between the alive check and the cmdline read;
`ps -ww` on macOS for a pid that just exited; `open --port` equal to the
installed port with no tray alive (must start it, not refuse); `open` with no
manifest and no plist (installed_port None → must not refuse); `open --port N`
on Windows/Linux where there is no plist but a manifest; `install --port 9000`
over an install on 8457 (must not refuse itself: the old manifest is deleted
before its own open; check the order); the Windows test file for any other
`signal.SIGUSR1` evaluated outside a POSIX guard. Tests that cannot fail;
fixtures that touch the real ~/.anyscribe; the same pattern elsewhere. Races,
aborts, state left behind. Docs/help/skill claims vs code after these changes.

YOU MAY RUN (read-only): `git -C <repo> log|diff|show`,
`cat`, `grep`, `sed -n`; `python3 -c` with PYTHONPATH=<repo>/src
to call PURE functions (tray.command_line_is with literal strings; tray.pid_is_anyscribe
with pids read from ~/.anyscribe/tray.pid and server.pid; desktop.installed_port();
tray.health_is_anyscribe against http://127.0.0.1:8457); `curl -s
http://127.0.0.1:8457/api/health`; `launchctl list | grep anyscribe`; `ls
~/.anyscribe ~/Library/LaunchAgents`. YOU MAY NOT: run pytest, build, install,
uninstall, `desktop open`, `desktop status`, toggle autostart, send any signal,
start any server, push, comment on the PR, or edit any file.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round-3 finding (F1, F2/W, F3, F4, F6; F5 declined) as FIXED / PARTLY /
   NOT FIXED / DECLINED-OK, one line of evidence each; then NEW defects the
   fixes introduced.
3. Findings, most severe first, numbered <prefix>1, <prefix>2... (prefix C for
   the correctness reviewer, F for the fit reviewer): severity (blocker /
   should-fix / nit, only these words); CONFIRMED or PLAUSIBLE; where
   (file:line); concrete scenario; the fix.
4. Answers to any questions in this brief (advice, not findings).
5. Pending owner checks (do not block the verdict).
6. What you could not check, and why; any check you could not run, as the exact
   command; what you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
