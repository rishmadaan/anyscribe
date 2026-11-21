# Target
- Repo ~/labs/projects/anyscribe, your worktree ~/labs/projects/anyscribe-wt/mac-2c-app on branch feat/mac-app-2c-app, based on feat/mac-app-shell at df94f5b (the reviewed shell, rebased on main). Commit there only, never on main, never push.
- In scope: desktop/ and docs/building/ (architecture.md, journal, _index.md). Out of scope: src/, ui/ (slice 2c-ui is building the screens in parallel), install.sh, install.ps1, pyproject.toml, CHANGELOG.md, BACKLOG.md.
- Test folders: desktop/test (yours), tests/ (do not touch).
- Every test uses a throwaway HOME; never touch the owner's real ~/.local/bin, shell profiles, ~/Library, ~/.claude or ~/.anyscribe. Keep every window hidden. Stop processes by the pid or group you started.
- Packet: this folder is in your worktree, uncommitted; commit it first and write proof.md here.
- Review target: branch feat/mac-app-2c-app at 867e61a (code head 3d1b6e0), diff df94f5b..867e61a.
- Lead evidence at 867e61a: npm test 85 pass 0 fail; the real ~/.local/bin/anyscribe (a uv symlink) and ~/.claude/skills/anyscribe untouched (dates unchanged).
- Bridge amendment made during the build (the builder's): terminal.turnOff({choice: "keep-current"|"restore"}) answers needsChoice; results may carry ok true with a reason; the engine command is install-skill. Sent to the 2c-ui builder.
