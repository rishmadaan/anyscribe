---
type: decision
tags: [desktop, electron, mac-app, engine, menu-bar]
tldr: "desktop/ is the Mac app shell: Electron 44.9.3, plain JavaScript, no other dependencies. It starts its own engine on 8470 (8471 beside desktop mode), refuses a taken port and any server whose health pid is not its child, restarts after crashes until three in a minute, asks before quitting during jobs (never treating an unreadable job list as empty), and gives the dashboard a small preload bridge. Found and fixed a quit that hung invisibly when no engine was running."
---

# Mac app shell (phase 2b)

## What was built

`desktop/` holds an Electron app that starts the anyscribe engine as its
child, shows the existing dashboard in its window and lives in the menu bar
(mockup menu direction A). The design is the approved mockup of 2026-11-20,
sections 2 (start window), 6 (menu bar), 7 (quitting) and 9 (the settings the
bridge serves). The dashboard's own Mac screens are slice 2c; this slice gives
them `window.anyscribeDesktop` (contract in `desktop/README.md`).

## Decisions

- **Three files of logic, split by what they need.** `logic.js` is pure (unit
  tests), `engine.js` needs only Node (tested against a fake engine, a Node
  script that answers `/api/health` and `/api/jobs` and can crash, hang, ignore
  stdin and SIGTERM, answer with another pid or die before it is ready, and
  through seams with fake children), `main.js` needs Electron (covered by the
  end-to-end run). The quit decision (`quitDecision`) lives in `logic.js` so the
  "never quit silently during jobs" guard is unit-tested.
- **Port guards.** The app refuses a port that answers or cannot be bound.
  (Round 0 also refused an engine announcing another port; round 1 replaced
  that with the pid check below.)
- **`--watch-stdin`.** Round 0 retried an engine without the flag; round 1
  removed that: the shell merges after slice 2a and always passes it.
- **Coloured dots are not template images.** macOS turns a template image
  monochrome, so the plain glyph stays a template (`trayTemplate.png`) and the
  amber and red dot variants come in a black-glyph and a white-glyph version,
  chosen by `nativeTheme.shouldUseDarkColors`. They are generated once by
  `scripts/make-icons.js` (Electron's nativeImage, run headless) and checked in.
- **Icons on Linux and the e2e.** A Linux tray icon goes through the desktop
  session's bus (it shows in the panel) or GTK with a display; neither is
  allowed on a machine someone is using. The e2e runs in "dock" mode with no
  display (`--ozone-platform=headless`) and no session bus; the menu's content
  is unit-tested instead.

## Bug found by the end-to-end run

Quitting while no engine was running (after "couldn't start") closed every
window and left the app running with nothing on screen. The quit decision
resolved within the microtasks of Electron's own `before-quit` emit, so the
inner `app.quit()` ran re-entrantly; when the outer handler returned
(prevented), Electron reset its quitting state, and with all windows closed the
app stayed alive. Fix: `setImmediate(() => app.quit())`. The e2e step "quitting
from couldn't start exits the app" fails with the fix removed.

## Measured

On this Linux machine, against the real engine (0.19.0, and slice 2a's branch
read-only): the dashboard rendered 0.3 to 0.6 s after the engine answered
health. With 2a's `--watch-stdin`, a SIGKILLed app took its engine with it;
without it the engine stayed up (expected, logged).

## Round 1 review fixes

Two reviewers (correctness and fit) raised 21 findings; 20 were upheld. The
ones that changed the design:

- **Unknown is not empty.** `jobs()` returned `[]` on a timeout, error or bad
  body, so a slow engine read as idle and quitting or restarting went ahead
  during a transcription. It now validates the list and returns null when it
  cannot know; Quit When Done and Restart engine wait, and an unknown list at
  quit asks a question (round 3: "anyscribe couldn't check which transcriptions
  are running", with Quit When Done, Stop and Quit, Cancel).
- **Quit decided at once.** `before-quit` was always prevented and decided
  later, which on a Mac would cancel every logout. It now decides from the last
  poll (at most 2 s old): idle quits go ahead and `will-quit` closes stdin and
  sends SIGTERM. Accepted limit: a job started in those 2 s is not asked about
  (the engine has one submitter, its own window; declined C5). During a
  logout, any question cancels the logout, because macOS is told before the
  answer comes (an Electron limit); after Stop and Quit, log out again.
- **One lifecycle at a time.** Overlapping restarts or a stop during a crash
  restart could orphan or double-start engines. Round 1 ran start, stop and
  restart through a queue with a generation number; round 3 replaced both (see
  below).
- **Ownership by pid.** Readiness needs slice 2a's `/api/health` `pid` to
  equal the spawned child. (Round 1 also sent `/api/shutdown` only to that
  child; round 3 removed the HTTP shutdown.)
- **Frames and redirects.** `will-frame-navigate` and `will-redirect` now
  apply the same origin rule as navigation and popups.
- **Login item from the system**, finished jobs remembered by id while
  hidden, logs that never throw, the default title bar for the dashboard
  window until 2c, and the menu laid out as the mockup draws it.

## Round 3: the supervisor rebuilt

The round 2 re-check found four more lifecycle gaps (a health answer accepted
after the child had exited, a shutdown request that could reach a server that
took the port after verification, a log error that never cleared and was never
checked by an append, a restart that adopted a stop's generation). A diagnosis
found the cause: the supervisor decided from remembered snapshots that each
needed a hand-placed re-check after every await, and its tests could not hold
a reply open while an event fired.

The rebuild decides from the child process. One current run record
(`this.run`) is set when a start or restart is accepted and cleared only by
that child's exit (or a failure before spawn). Every late continuation (port
check, health answer, readiness timeout, the jobs read inside restart) passes
one gate, `run === this.run && !run.cancelled`, and the exit handler clears
`this.run` first, so a late "ours" is dropped. One exit handler kills the dead
engine's process group and decides what next. One stop closes stdin, sends
SIGTERM to the group and SIGKILLs it after 10 s, with no HTTP request (closing
stdin already does what `/api/shutdown` did). A second restart while one is
pending is refused, not queued. The log is probed with an empty append before
every launch, so Try again sees a repair. The constructor takes seams
(`spawn`, `health`, `jobs`, `killGroup`), and every supervisor test ends with
an invariant check: at most one live child, and "running" only while its child
is alive.

The same round: failed jobs sort first in the "finished while closed" rows,
waiting and quitting rows are capped at 5 plus "and N more", and the menu
header ends "· not answering" after three failed job reads in a row.

## Round 4

An explicit stop now revokes a restart's pending relaunch. Stop and Quit quits
straight away, with no job read and no per-job cancel requests: jobs live only
in the engine's memory, a cancel is a flag read at the job's next progress
event, and the engine's stop (stdin closed, SIGTERM to its group) ends every
job moments later, so the cancels only added waiting (about 2 s per job when
the engine is not answering). The cap lines now say "and N more waiting" or
"and N more finished", and an idle engine that is not answering reads
"anyscribe · Not answering" instead of "Ready · not answering".

## Left for later

- Phase 3: packaging and the bundled Python; stamp the app version from
  `pyproject.toml` at packaging so `desktop/package.json` and the engine
  cannot drift (F8); a small application menu (anyscribe: About, Open Cmd O,
  Quit Cmd Q; Edit; Window) in place of Electron's default (F12).
- Slice 2c: the dashboard's Mac screens and banner, a drag area so the
  dashboard window can use the hidden-inset title bar, and hiding the
  dashboard's own Shutdown button in the app.
- On a real Mac: logout with the app idle, the login launch
  (`wasOpenedAtLogin` on macOS 13 and later), the tray menu and dots, Dock
  modes, and the start window's look.
