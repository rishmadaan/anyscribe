# Lens

## Every review
- Is this the job he asked for? (The approved mockup's shell behaviour, sections 2, 6, 7 and 9, direction A; nothing from slice 2c.)
- Use it the way he will: open the app from Finder (no Terminal PATH), close the window, transcribe from the menu bar's view, quit mid-job, log out, open it twice, force-quit it, start it at login, switch the Dock mode.
- Claims worded stronger than their evidence.

## Code PR
- His goals as invariants:
  1. The engine never outlives the app, never runs twice, and the shell never stops a process it did not start (by pid only).
  2. The shell never connects to, or stops, something else holding its port.
  3. Nothing a web page can do inside the window reaches anything beyond the bridge, and nothing outside 127.0.0.1:<port> runs in the window.
  4. A quit, logout or crash never silently loses a running transcription; the quit question's counts match the engine's list.
  5. The approved wording and states (mockup sections 2, 6, 7, 9) appear as drawn, except where Electron cannot (say which).
  6. Everything is stored in the right place: logs in ~/.anyscribe/logs/app.log, settings in Electron's userData, never inside the app bundle.
- Try to break it with: a port held by another program; an engine that exits instantly, one that hangs before answering, one that announces a different port; three crashes in 59 s versus 61 s; quitting during start; quitting with no engine; a second launch while starting; the dashboard's own Shutdown button; navigation to http://127.0.0.1:<port>.evil.example/, to file://, to another local port; window.open; a bridge call from an iframe or a navigated page; revealInFinder with a relative path or a path outside the home folder; the jobs list missing (404) or malformed.
- Tests that cannot fail (a check that passes with its guard removed), a test environment unlike the real one (fake engine versus real engine; Linux versus macOS).
- Races, aborts, state left behind (timers, intervals, child processes, listeners, tray icons).
- Security boundary: navigation, window.open, IPC sender checks, the preload surface, external URL schemes passed to shell.openExternal.
- Docs and spec that claim more than the code does.
