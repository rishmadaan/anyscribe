You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: <repo>/tests, <repo>/.venv,
<repo>/ui/node_modules. Skip any repo startup
routine; read only what this brief names (and files they point you to).

ROUND 3, the closing round, of a size-L PR merge review (cap 4). Rounds 1 and
2 (two reviewers each, all NOT YET) are settled below. Check that each round-2
fix is real (read the code, probe it, try to break it with concrete inputs),
and look for anything new, especially problems the fixes introduced. Say GOOD
TO GO only if you would merge it yourself.

WHAT: repo <repo>, branch feat/desktop-mode at commit
240766b (full: `git -C <repo> rev-parse HEAD`). Round 2
reviewed 273be39; the round-2 fix wave is `git diff 273be39..240766b` (7 commits).
The whole change is `git diff main...240766b`. PR #22 (draft):
https://github.com/rishmadaan/anyscribe/pull/22. Everything is frozen.

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

SETTLED, DO NOT REOPEN:
- No signed downloadable app (owner's decision; parked in BACKLOG).
- Tray's missing-extra exit stays 1 (install paths refuse without the extra).
- `uninstall-service` / the Settings toggle never stop a running tray.
- plist: ProcessType Interactive (measured), KeepAlive SuccessfulExit=false,
  ThrottleInterval 10 (launchd default; a click within a minute of Quit comes
  back under launchd: measured 2 s).
- macOS install writes the login item first and launchd starts the tray.
- F5: plist keeps a copy of the installing shell's PATH (documented).
- Identity on the wire: `app: "anyscribe"` on /api/health; explicit foreign
  `app` always rejects; legacy pre-0.18 shape (`version` str + `dependencies`
  dict, no `app`) accepted as a compatibility heuristic so an upgraded user's
  old server is still recognised until they re-run `desktop install`.
- Process identity: command-line regex (`-m anyscribe` or a script named
  anyscribe/scribe/ascli, optionally quoted on Windows) plus the role token
  `tray` or `ui`; no creation-time check (accepted: the realistic risks are
  the interpreter-path and wrong-role cases, both now covered).
- `desktop open --port N` refuses when desktop mode is installed on another port.
- Windows click-through on a real PC: deferred by the owner; CI's
  windows-latest job is the Windows check. Linux stranger test: blocked (the
  Linux box is offline); GLib's real parsers were run on the .desktop text.

PRIOR ROUNDS (round-2 findings, the response, and the builder's claimed evidence,
to be checked):
- W/F8 (Windows test referenced signal.SIGUSR1): FIXED, test computes the
  expected signal with getattr / skips the posix param on win32.
- C1/F12 (substring identity; alias rejected): FIXED. `pid_is_anyscribe(pid, role)`
  with the regex above; `read_pidfile` role "tray", server pid role "ui";
  real-child tests: an interpreter path containing "anyscribe" is NOT a tray and
  survives stop_tray (children print "ready" first to avoid the macOS re-exec
  race); a wrong-role command is not a tray; `scribe tray`, `ascli tray` and
  `"...\anyscribe.exe" tray` match.
- C2/F10 (`open --port N` killed the installed instance): FIXED.
  `PortMismatch` raised in `open_dashboard` before any signal or stop, with the
  exact message "anyscribe is installed on port {installed}. Run `anyscribe
  desktop open` (no --port) to open it, or `anyscribe desktop install --port
  {port}` to move it." Builder addition: `install()` deletes the old manifest right
  after tearing down the old install (a macOS reinstall to a new port otherwise
  hit PortMismatch from its own open); the test fixture now points
  `service.plist_path` at a tmp file. Lead evidence on this Mac: `desktop open
  --port 9000` → exit 1 in 0 s with that message; tray pid unchanged; 8457 healthy.
- C3/F9 (losing duplicate tray exit 0 → bare `ui` spawn): FIXED. `_await_health`
  returns "exited-ok" for returncode 0; open waits for the winner; bare `ui` only
  on non-zero exit. Lead evidence: login item off, tray quit, two simultaneous
  `desktop open` → both exit 0 in 2-3 s, exactly one tray and one server on
  8457, the loser logged "already running", no "busy"/8458.
- C4 (legacy shape overrode explicit foreign `app`): FIXED; explicit `app` wins;
  legacy needs typed fields; real-server tests for `{"app":"another-program",...}`
  and `{"version":null,"dependencies":null}` → foreign.
- C5/F14 (restart lock skipped startup/teardown; `starting` guard untested):
  FIXED. `closing` flag + one lifecycle lock across `_start_server`, restart and
  teardown; the builder found the brief's C5 test exercised the lock, not
  `closing`, and added two tests (teardown without the lock leaves server 4001
  alive; a restart queued behind a paused teardown without `closing` spawns
  4001), plus the `starting` sibling test. Quit may take up to ~8 s if a server
  ignores /shutdown (by design).
- C6/F11/F13/F15 docs: FIXED with the exact wordings (uninstall copy, `--no-launch`
  comment, architecture.md security claim + supervision + install order, skill
  Quit/teardown sentence, lock-not-pidfile explanations in skill and user
  troubleshooting, configuration.md inventory rows, CHANGELOG/troubleshooting
  prose de-duplicated); the `open --port` refusal documented in skill and user
  docs; `landing/docs` regenerated.

SOURCES (absolute paths; read, run nothing that writes):
- Round-2 reports: <repo>/docs/reviews/2026-10-22-desktop-mode-pr22/report-gpt-6.1-sol-r2.md
  and .../report-fable-r2.md; round-1 reports in the same folder (r1).
- Fix brief and builder report: .../fix-brief-r2.md and
  <repo>/.superpowers/sdd/2026-10-22-desktop-mode/review-fix-r2-report.md
- Design: <repo>/docs/superpowers/specs/2026-10-22-desktop-mode-design.md
- Code: src/anyscribe/core/{desktop,service,launcher,tray}.py,
  src/anyscribe/cli/{desktop_cmd,service_cmd,tray_cmd,main}.py,
  src/anyscribe/web/{app.py,routes/system.py,routes/health.py}, install.sh,
  install.ps1, .github/workflows/ci.yml.
- Tests (read only): tests/test_desktop.py, test_launcher.py, test_tray.py,
  test_autostart_route.py, test_install_sh.py, test_web.py.
- Docs: docs/user/{getting-started,commands,troubleshooting,configuration,agents}.md,
  README.md, CHANGELOG.md, BACKLOG.md, src/anyscribe/skill/SKILL.md and
  src/anyscribe/skill/references/{commands,troubleshooting}.md,
  docs/building/architecture.md, docs/building/journal/2026-10-22-desktop-mode.md.
- Lead evidence: CI on 240766b was triggered by the push just before this brief
  (the lead attaches the result at relay; your verdict is conditional on it);
  on 273be39 every job was green except windows-latest, which failed only on
  the W/F8 test line (115 Windows tests passed, including the real lock, the
  real `anyscribe tray` with the lock held, the real sleeper not signalled, the
  pythonw stream probe, the shortcut and the pid probe). The 14-check script
  passed 14/14 on 240766b after a reinstall.

LENS:
Every review: is this the job he asked for; use it the way he will (an
editable pip install of this branch; `anyscribe` on PATH); claims worded
stronger than their evidence.
Code PR, closing round: for each FIXED item above, read the code and try to
break it with: a pidfile naming a `python -c` under a path containing
"anyscribe"; a pidfile naming `anyscribe https://...` (wrong role); `scribe tray`;
Windows `"C:\...\Scripts\anyscribe.exe" tray` (case); a health body with
`app: "ANYSCRIBE"` (case) or `app: ""`; the pre-0.18 shape with `dependencies`
as a list; `open --port` equal to the installed port (must still work); a
spawned tray that exits 0 before the winner's server binds, and one that exits
1; Quit during a signal restart; a manifest deleted mid-reinstall when
`install_service` then fails (what does status say; is anything stranded); the
Windows uninstall path with a stale server.pid; the launcher script run from
Finder with a minimal PATH; `desktop open` under pythonw. Tests that cannot
fail; fixtures that touch the real ~/.anyscribe or LaunchAgents; the same
pattern elsewhere. Races, aborts, state left behind. Docs/help/skill claims vs
code after these changes, including the exact copy strings.

YOU MAY RUN (read-only): `git -C <repo> log|diff|show`,
`cat`, `grep`, `sed -n`; `python3 -c` with PYTHONPATH=<repo>/src
to import and call PURE functions (render_*, desktop_quote, service_path,
tray.health_is_anyscribe against http://127.0.0.1:8457, tray.pid_is_anyscribe
with pids you read from ~/.anyscribe/tray.pid and server.pid, the command-line
regex with literal strings); `curl -s http://127.0.0.1:8457/api/health`;
`launchctl list | grep anyscribe`; `ls ~/Applications ~/Library/LaunchAgents
~/.anyscribe`. YOU MAY NOT: run pytest, build, install, uninstall, `desktop
open`, `desktop status` (its CLI callback may refresh skill files), toggle
autostart, send any signal, start any server, push, comment on the PR, or edit
any file.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every round-2 finding (W/F8, C1/F12, C2/F10, C3/F9, C4, C5/F14, C6, F11,
   F13, F15) as FIXED / PARTLY / NOT FIXED / DECLINED-OK, one line of evidence
   each; then NEW defects the fixes introduced.
3. Findings, most severe first, numbered <prefix>1, <prefix>2... (prefix C for
   the correctness reviewer, F for the fit reviewer): severity (blocker /
   should-fix / nit, only these words); CONFIRMED or PLAUSIBLE; where
   (file:line); concrete scenario; the fix (exact wording for documents).
4. Answers to any questions in this brief (advice, not findings).
5. Pending owner checks (do not block the verdict).
6. What you could not check, and why; any check you could not run, as the exact
   command; what you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
