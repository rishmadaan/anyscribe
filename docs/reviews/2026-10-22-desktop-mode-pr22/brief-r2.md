You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: <repo>/tests, <repo>/.venv,
<repo>/ui/node_modules. Skip any repo startup
routine; read only what this brief names (and files they point you to).

ROUND 2 of a size-L PR merge review. Round 1 (two reviewers, both NOT YET) is
settled below. Check that each fix is real (read the code, probe it, try to
break it with concrete inputs), and look for anything new, especially problems
the fixes introduced.

WHAT: repo <repo>, branch feat/desktop-mode at commit
273be39 (full: run `git -C <repo> rev-parse HEAD`).
Round 1 reviewed 24a5322; the fix wave is `git diff 24a5322..273be39` (7 commits).
The whole change is `git diff main...273be39`. PR #22 (draft):
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
- Two trays, or a relaunch loop.
- The dashboard opens onto a program that is not anyscribe; anyscribe signals a
  process that is not its own.
- Toggling "Start at login" off kills the dashboard the user is looking at.
- Anything under ~/anyscribe/, config.yaml or .env touched by install/uninstall.
- Claude Code or the MCP server needing the desktop app to be running.
- Money, signing, or a new runtime dependency.
- A doc, help text or skill file that claims more than the code does.

SETTLED, DO NOT REOPEN:
- No signed downloadable app (owner's decision; parked in BACKLOG).
- Tray's missing-extra exit stays 1 (install paths refuse without the extra).
- `uninstall-service` / the Settings toggle never stop a running tray.
- plist: ProcessType Interactive (measured), KeepAlive SuccessfulExit=false,
  ThrottleInterval now 10 (launchd's default; see C-fix evidence below).
- macOS install writes the login item first and launchd starts the tray.
- F5 (plist keeps a copy of the installing shell's PATH): DECLINED-OK, documented
  in troubleshooting; pruning risks dropping a path a tool needs.
- Windows click-through on a real PC: deferred by the owner; CI's windows-latest
  job (real .lnk, real _pid_alive, install.ps1 parse, and now the lock/stream
  tests) is the check.
- Linux stranger test: blocked, the Linux box is offline; GLib's real key-file and
  Exec parsers were run on the generated .desktop text.

PRIOR ROUNDS: round-1 findings, the response to each, and the builder's claimed
evidence (treat every claim as a claim to check):
- F1/C6 (orphaned tray after dashboard Shutdown; app click waited 15 s then
  failed): FIXED. open_dashboard's orphan branch now sends SIGUSR1 to the live
  tray (POSIX), which restarts its server under a lock; fallback stop+start only
  if health stays down; Windows uses stop+spawn. Lead evidence on this Mac after
  reinstall: Shutdown then `desktop open` → exit 0 in 5 s, same launchd-owned
  tray pid before and after, fresh server.pid, health ok.
- F2 (upgrade with a running login-item tray kept the old tray; launchctl
  printed "Load failed: 5"): FIXED. install stops a running tray even without a
  manifest; `_launchctl` captures output and prints one plain line on failure.
  Lead evidence: manifest removed, old tray running → install: old pid gone,
  launchd owns the new tray, no raw launchctl text, "Starts at login: yes".
- F3 (getting-started sent installer users to `anyscribe ui`): FIXED, wording
  per the reviewer.
- F4 (open after Quit spawned outside launchd): FIXED via `_start_tray` →
  plain `launchctl kickstart` (no -k) when the login item serves that port.
  Lead evidence: Quit, then two simultaneous `desktop open` → both exit 0 in
  2 s, exactly one tray, launchd-owned, health ok.
- F6 (plist path and macOS words shown to every user): FIXED (install prints
  "Starts at login: yes"; help text; Settings caption platform-neutral; bundle rebuilt).
- F7 (headless Linux `curl | bash`): FIXED (install.sh skips desktop mode when
  DISPLAY and WAYLAND_DISPLAY are both empty, with a message).
- C1 (stale pidfile pid reuse → signal an unrelated process): FIXED.
  `pid_is_anyscribe(pid)` (POSIX: ps command line; Windows: Win32_Process
  CommandLine) gates `read_pidfile` and every signal; non-positive pids
  rejected; test with a real unrelated child that must survive.
- C2 (identity: any `version` JSON passed; tray attached/Open UI/shutdown to
  any listener): FIXED. /api/health returns `app: "anyscribe"`; identity =
  200 and (app == anyscribe OR the pre-0.18 shape `version` + `dependencies`);
  `{"version": "1"}` alone is foreign (real local HTTP server in the test);
  tray attaches only to identified anyscribe, else status "port N is used by
  another program"; Open UI and shutdown POST only to identified anyscribe.
- C3 (double-click → two trays; pidfile is not a lock): FIXED. The tray holds a
  non-blocking exclusive OS lock (fcntl.flock / msvcrt.locking) on
  ~/.anyscribe/tray.lock for its lifetime; the second instance exits 0. Real
  two-process test asserts which child got the lock. Lead evidence above.
- C4 (pythonw: sys.stdout None → uvicorn logging setup crashes; lead verified
  the crash): FIXED. `ensure_streams()` opens tray.log for missing streams in
  the tray and in web.app.run; the tray spawns its server with stdin DEVNULL and
  stdout/stderr to tray.log; subprocess test runs uvicorn.Config with stdout None.
- C5 (Windows hard-kill left a job thread finishing): FIXED. The tray writes
  ~/.anyscribe/server.pid; stop_tray terminates the identified server pid too
  and waits for the port.
- C7 (checkpoint-resume copy overstated): FIXED, new copy: "Stopped anyscribe.
  If a transcription was running, it was interrupted: run it again (long jobs
  reuse the chunks they already finished)." in CLI, docs and skill.
- C8 (`healthy` ignored processes): FIXED. healthy = installation intact AND the
  dashboard answers; reason "Installed but not running. Click the anyscribe app
  or run: anyscribe desktop open". Lead evidence: after Shutdown, status
  reported healthy false with that reason.
- C9 (`--no-launch` wording): FIXED with the reviewer's exact text in help,
  SKILL.md, commands.md and the skill reference.
- C10 (security-prompt claims): FIXED with the reviewer's exact wording in
  CHANGELOG, troubleshooting and the journal.
- Builder deviations to weigh: `_launchctl` also prints its line when launchctl
  writes to stderr with exit 0 (macOS 26 `load`/`unload` exit 0 on failure);
  `_kickstart` runs only when the login item's port matches; a signal restart is
  skipped while the tray's own server process is alive but not yet answering
  (so a second click cannot kill a server the first click just started);
  `ensure_streams` replaces only the missing stream.

SOURCES (absolute paths; read, run nothing that writes):
- Round-1 reports: <repo>/docs/reviews/2026-10-22-desktop-mode-pr22/report-gpt-6.1-sol-r1.md
  and <repo>/docs/reviews/2026-10-22-desktop-mode-pr22/report-fable-r1.md
- Fix briefs: <repo>/docs/reviews/2026-10-22-desktop-mode-pr22/fix-brief-r1.md
- Builder reports (claims): <repo>/.superpowers/sdd/2026-10-22-desktop-mode/review-fix-r1-report.md
  and <repo>/.superpowers/sdd/2026-10-22-desktop-mode/review-fix-r1b-report.md
- Design: <repo>/docs/superpowers/specs/2026-10-22-desktop-mode-design.md
- Code: src/anyscribe/core/{desktop,service,launcher,tray}.py,
  src/anyscribe/cli/{desktop_cmd,service_cmd,tray_cmd,main}.py,
  src/anyscribe/web/{app.py,routes/system.py,routes/health.py}, install.sh,
  install.ps1, .github/workflows/ci.yml (under the repo).
- Tests (read only): tests/test_desktop.py, test_launcher.py, test_tray.py,
  test_autostart_route.py, test_install_sh.py, test_web.py.
- Docs: docs/user/{getting-started,commands,troubleshooting,agents}.md, README.md,
  CHANGELOG.md, BACKLOG.md, src/anyscribe/skill/SKILL.md and
  src/anyscribe/skill/references/{commands,troubleshooting}.md,
  docs/building/architecture.md, docs/building/journal/2026-10-22-desktop-mode.md.
- Lead evidence: CI run 39808100206 on 273be39 (in progress at brief time; the
  lead will attach the result to the relay; your verdict is conditional on it);
  a 14-check script written by another model and run by the lead passed 14/14
  on 273be39 (status, bundle/plist/manifest, health+ffmpeg, toggle off keeps the
  tray, toggle on, foreign-port refusal, single tray on open, duplicate tray
  exits 0, reinstall replaces the tray); with the foreign-port refusal
  deliberately disabled (round 1 code) its check 5 failed.

LENS:
Every review: is this the job he asked for; use it the way he will (an
editable pip install of this branch; `anyscribe` on PATH); claims worded
stronger than their evidence.
Code PR, round 2: for each FIXED item, read the code and try to break it with:
a stale pidfile holding a reused pid of a non-anyscribe process; a pidfile
holding the pid of `scribe tray` (the alias; does `pid_is_anyscribe` see it?);
a foreign HTTP server answering `{"version":"1"}`; a pre-0.18 server answering
`{"ok","version","dependencies"}`; two trays started within 50 ms (lock); the
tray's server alive but not yet answering when SIGUSR1 arrives; Quit then click
within 10 s; `desktop open --port 9000` when the login item serves 8457; a
Windows session where `sys.stdout is None` (trace `ensure_streams` and every
print in the tray path); `stop_tray` when server.pid is stale; uninstall while
a transcription runs on POSIX and on Windows; the `-k`-less kickstart when the
job is already running. Tests that cannot fail; fixtures that touch the real
~/.anyscribe; the same pattern elsewhere (any other `os.kill`, any other port
probe without identity, any other place that spawns a child without streams).
Races, aborts, state left behind (tray.lock, server.pid, pidfile after a crash).
Docs/help/skill claims vs code after these changes.

YOU MAY RUN (read-only): `git -C <repo> log|diff|show`,
`cat`, `grep`, `sed -n`; `python3 -c` to import and call PURE functions with
PYTHONPATH=<repo>/src (render_plist, desktop_quote,
render_desktop_entry, render_shortcut_script, service_path, and
tray.health_is_anyscribe against http://127.0.0.1:8457); `anyscribe desktop
status --json`; `curl -s http://127.0.0.1:8457/api/health`; `launchctl list |
grep anyscribe`; `ls ~/Applications ~/Library/LaunchAgents ~/.anyscribe`. YOU
MAY NOT: run pytest, build, install, uninstall, `desktop open`, toggle
autostart, send any signal, start any server, push, comment on the PR, or edit
any file.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Every earlier finding (F1-F7, C1-C10) as FIXED / PARTLY / NOT FIXED /
   DECLINED-OK, one line of evidence each (file:line or probe output); then NEW
   defects the fixes introduced.
3. Findings, most severe first, numbered <prefix>1, <prefix>2... (prefix C for
   the correctness reviewer, F for the fit reviewer): severity (blocker /
   should-fix / nit, only these words); CONFIRMED or PLAUSIBLE; where
   (file:line); concrete scenario; the fix (exact wording for documents).
4. Answers to any questions in this brief (advice, not findings).
5. Pending owner checks (do not block the verdict).
6. What you could not check, and why; any check you could not run, as the exact
   command; what you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
