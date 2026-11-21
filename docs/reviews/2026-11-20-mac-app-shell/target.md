# Target

- Repo: ~/labs/projects/anyscribe, base commit 7ab1539 (main, v0.19.0). Your worktree is ~/labs/projects/anyscribe-wt/mac-shell on branch feat/mac-app-shell; commit there only, never on main, never push.
- In scope: a new desktop/ folder; docs/building/ (architecture.md, journal, _index.md); .gitignore (desktop/node_modules); the root README only if a one-line pointer helps.
- Must not change: anything under src/ (slice 2a changes the engine in parallel), ui/, install.sh, install.ps1, pyproject.toml, CHANGELOG.md, BACKLOG.md.
- Test folders: tests/ (do not touch) and desktop's own tests.
- Never stop a process by matching its name or command line; stop the engines you start by the pid you started. Use a throwaway HOME for every engine you start, never the real ~/.anyscribe. Keep every window hidden.
- Packet: this folder (docs/reviews/2026-11-20-mac-app-shell/) is already in your worktree, uncommitted; commit it as your first commit and write proof.md there.
- Review target: branch feat/mac-app-shell at 880ed2c365247cc719be6140a9e810c93d9a8521, diff 7ab1539..880ed2c (worktree ~/labs/projects/anyscribe-wt/mac-shell).
- Lead evidence at that sha: `npm test` in desktop/: 27 pass, 0 fail.
- Engine side for reference (read-only): branch feat/mac-app-engine in ~/labs/projects/anyscribe-wt/mac-engine (slice 2a, under its own review).
