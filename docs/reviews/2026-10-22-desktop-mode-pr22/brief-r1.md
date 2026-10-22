You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: <repo>/tests, <repo>/.venv,
<repo>/ui/node_modules. Skip any repo startup
routine; read only what this brief names (and files they point you to).

WHAT: repo <repo>, branch feat/desktop-mode at
commit 24a532220c0ea2e7594e8da8ee0193cd8d5b1780 (short 24a5322), GitHub PR #22
(https://github.com/rishmadaan/anyscribe/pull/22, draft). The change is
`git diff main...24a5322` in that repo (about 30 commits). Everything is
frozen; nobody edits while you read.

WHY IT EXISTS (the owner's ask, in his words): "AnyScribe currently runs by
opening the terminal. Is there a way that we can run it without opening the
terminal, possibly with a web app, just like how Lantern runs? We will also
have to set up a background service that runs with that web app." Then:
"realistically, if a user has to know all of this in order to use it, it is
never going to be used." Then: "if it requires so much signing and all of those
things, then we should not build. I don't want to pay anything right now. Since
I am the only Mac user (maybe one more Mac user), I'm okay with shipping with
the 'open anyway' thing." And: "AnyScribe itself can come up with two different
install methods: one that ships through pip, which is just the CLI version;
a desktop mode that also ships through that. Desktop mode basically will
install it as an app. Also, I'm worried about the fact that if we don't open
the app and Claude wants to call it, how will that work?"

FIRST QUESTION: is this the job he asked for, and the right instrument for it?
If the brief, the goal or the spec is wrong, say so instead of reviewing around it.

MUST NEVER HAPPEN:
- A user has to know about a server, a tray, a login item or a PATH to use it.
- A login-started anyscribe that cannot find ffmpeg or Deno (that was the
  original bug: launchd gives a minimal PATH).
- Two trays, or a relaunch loop (the plist has KeepAlive SuccessfulExit=false).
- The dashboard opens onto a program that is not anyscribe.
- Toggling "Start at login" off kills the dashboard the user is looking at.
- Anything under ~/anyscribe/ (the vault), config.yaml or .env touched by
  install or uninstall.
- Claude Code or the MCP server needing the desktop app to be running.
- Money, signing, or a new runtime dependency.
- A doc or skill file that claims more than the code does.

SETTLED, DO NOT REOPEN (each with its reason):
- No signed downloadable app, no Apple Developer Program, no Windows
  certificate: owner's decision; parked in BACKLOG.
- The tray's missing-extra exit stays 1 (install paths refuse without the
  extra; ThrottleInterval 60 bounds the loop; documented).
- `uninstall-service` / the Settings toggle never stop a running tray; only
  `desktop uninstall` stops (the toggle lives inside the dashboard the tray serves).
- plist has ProcessType Interactive: measured on this Mac, a plain launchd job
  throttles child processes (/api/health 5 to 13 s vs 0.32 s).
- macOS install writes the login item first and lets launchd start the tray
  (so crash restart applies from the first session); Windows/Linux spawn first.
- `stop_tray` waits for the old pid to exit and the port to free (a live
  reinstall failed without it: the new tray attached to the dying server).
- App icon: the "sound becomes text" mark, chosen by the owner from five options.
- Windows click-through on a real PC is deferred by the owner; the Windows CI
  job (real .lnk creation, real _pid_alive, install.ps1 parse) is green.
- Linux stranger test is blocked (the Linux box is offline); GLib's real
  key-file + Exec parsers were run on the generated .desktop text instead.
- Known limits listed in docs/user/troubleshooting.md and the journal are
  accepted as limits, not defects, unless you show one is worse than stated.

SOURCES (absolute paths; read, do not run anything that writes):
- Design: <repo>/docs/superpowers/specs/2026-10-22-desktop-mode-design.md
- Plan: <repo>/docs/superpowers/plans/2026-10-22-desktop-mode.md
- Build ledger with every ruling and deferred minor (treat as claims):
  <run folder>/sdd-ledger.md
- Journal: <repo>/docs/building/journal/2026-10-22-desktop-mode.md
- Code: src/anyscribe/core/{desktop,service,launcher,tray}.py,
  src/anyscribe/cli/{desktop_cmd,service_cmd,tray_cmd,main}.py,
  src/anyscribe/web/routes/system.py, install.sh, install.ps1,
  .github/workflows/ci.yml, src/anyscribe/config/paths.py (all under the repo).
- Tests: tests/test_desktop.py, test_launcher.py, test_tray.py,
  test_autostart_route.py, test_install_sh.py (read only).
- Docs: docs/user/{getting-started,commands,troubleshooting,agents}.md, README.md,
  CHANGELOG.md, BACKLOG.md, src/anyscribe/skill/SKILL.md and
  src/anyscribe/skill/references/{commands,troubleshooting}.md,
  docs/building/architecture.md.
- Lead evidence (claims for you to weigh, not proof):
  * CI run 39777981708 on this exact SHA: all jobs green (ubuntu 3.11/3.12/3.14,
    frontend, docs, desktop-platforms macos-latest and windows-latest).
  * Live on this Mac today: `anyscribe desktop install --yes` from PATH; app
    bundle, plist, icons, manifest written; /api/health from the launchd-started
    server reports ffmpeg true; a 2 s spoken clip transcribed through the
    dashboard API (deepgram) and written to the vault; launchctl unload/load as
    a logout stand-in; reinstall over a running install succeeds in 3.6 s with
    the old tray gone and launchd owning the new one; Quit (SIGTERM) leaves
    `launchctl list` at `- 0` with no relaunch in 76 s.
  * A 14-check script written by another model and run by the lead passed
    14/14; with the foreign-port refusal deliberately disabled, its check 5
    failed; restored, it passed again.
  * Each task had a mutation-tested guard (details in the ledger).

LENS:
Every review:
- Is this the job he asked for?
- Use it the way he will: the shipped build, installed, on his device, by his
  path, with no test hooks. Which copy does his device actually load? (Here:
  an editable pip install of this branch; `anyscribe` on PATH is
  /Library/Frameworks/Python.framework/Versions/3.13/bin/anyscribe.)
- Claims worded stronger than their evidence.
Code PR:
- His goal written as invariants (MUST NEVER HAPPEN above); name any change
  that breaks one.
- Try to break each fix with concrete inputs: a home path with a space and an
  apostrophe; a home path with a curly apostrophe on Windows; a foreign program
  on 8457; a stale pidfile whose pid was reused; `desktop install --port 9000`
  then `desktop open` with no flag; `desktop uninstall` while a job runs; pip
  upgrade then `desktop status`; Python reinstalled (manifest python missing);
  `install-service` without the tray extra; toggle off/on in the Settings page
  while the tray is running; `--no-launch` on macOS; the installer with
  `--no-desktop`, with `--method git`, and with `desktop install` failing;
  a `.desktop` Exec with `%`, `$`, `"` and `\` in the path; two `desktop open`
  clicks within a second; `desktop install` from a Finder-launched shell with a
  minimal PATH.
- Tests that cannot fail (a check that passes with its guard removed), N/A
  entries hiding checks that could run, a test environment unlike the real one.
- Fixture tests must set test-owned home folders, pidfiles, log paths and ports
  in their shared defaults, so no case silently uses the real ~/.anyscribe.
- The same pattern elsewhere: any other place that assumes POSIX paths, a
  POSIX-only signal call, shell quoting, or that reads the real home.
- Races, aborts, state left behind: launchd vs spawned tray; stop_tray vs the
  new tray; half-install when open fails; icon cache; pidfile ownership.
- Security boundary: the launcher scripts and shortcuts embed paths; the
  dashboard binds 127.0.0.1 only; /api/autostart and /api/shutdown are
  unauthenticated local endpoints (pre-existing; say if the change widens them).
- Docs and spec that claim more than the code does; spec that was wrong and
  got built anyway (the ledger records several corrections; check nothing is left).
- CI on this exact SHA; a merge verdict is conditional on it.
Live system (the login item is unattended automation):
- False-green health: what reads healthy while broken? (`desktop status`
  "healthy" vs processes; health endpoint vs a server that cannot transcribe.)
- Reboot, dependency down, Python upgraded, port taken: is each loud and documented?

YOU MAY RUN (read-only): `git -C <repo> log|diff|show`,
`cat`, `grep`, `sed -n`, `plutil -lint` on a file you write to /tmp is NOT
allowed (write nothing); `python3 -c` to import and call PURE render functions
from the repo (render_plist, render_desktop_entry, desktop_quote,
render_shortcut_script, render_app_script, service_path) with
PYTHONPATH=<repo>/src is fine; `anyscribe desktop
status --json` and `curl -s http://127.0.0.1:8457/api/health` and
`launchctl list | grep anyscribe` and `ls ~/Applications ~/Library/LaunchAgents`
are read-only and allowed. YOU MAY NOT: run pytest, build, install, uninstall,
`desktop open`, toggle autostart, kill anything, push, comment on the PR, or
edit any file.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Findings, most severe first, numbered <prefix>1, <prefix>2... (prefix C for
   the correctness reviewer, F for the fit reviewer): severity (blocker /
   should-fix / nit, only these words); CONFIRMED (you reproduced or traced it)
   or PLAUSIBLE; where (file:line); what goes wrong, as a concrete scenario;
   the fix (for documents, the exact replacement wording).
3. Answers to any questions in this brief (advice, not findings).
4. Pending owner checks: things only the owner can confirm. They do not block
   the verdict.
5. What you could not check, and why; any check you could not run, as the
   exact command, so the lead can run it for the next round. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
