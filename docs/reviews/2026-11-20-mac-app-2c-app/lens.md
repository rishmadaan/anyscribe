# Lens

## Every review
- Is this the job he asked for? (The app-side mechanics behind the approved mockup sections 3, 4, 5 and 9; bridge-v2.md; nothing more.)
- Use it the way he will: a Mac that already has desktop mode and a uv-installed anyscribe at ~/.local/bin/anyscribe, zsh as the login shell, Claude Code installed; then the same on a fresh Mac with neither.
- Claims worded stronger than their evidence.

## Code PR
- His goals as invariants:
  1. Nothing the person owns is overwritten or deleted without asking: a command that is not ours, a shell profile line, a skill folder that Terminal still needs, the old launcher's pieces beyond what `desktop uninstall` removes.
  2. Turning the Terminal switch off returns the Mac to exactly what it was (the replaced command back, no stray PATH line duplicated, the skill gone only when nothing else needs it).
  3. The status the screens will show is true: what Terminal actually runs, whether the skill is there, which launcher pieces are really gone.
  4. The app's own engine is never stopped or confused by the old launcher's removal.
  5. Files opened with the app are never lost or delivered twice.
  6. The reviewed shell supervisor's design (2b) is intact.
- Try to break it with: a symlink at ~/.local/bin/anyscribe into a uv tool; a plain file there; a file with our marker but a changed body; a ~/.zprofile that already has the line in a different form; bash with an existing ~/.profile; fish; a login shell whose rc files print noise or hang; ~/.claude absent; a desktop.json whose port is 8470; a tray.pid pointing at an unrelated process; open-file before the window exists and twice for the same file.
- Tests that cannot fail; test environments unlike the real one (Linux vs macOS login shells, path_helper).
- Security boundary: the bridge handlers' sender checks for the new members; any path the page can pass to them.
- Docs and spec that claim more than the code does.
