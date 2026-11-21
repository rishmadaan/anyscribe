# Target
- Repo ~/labs/projects/anyscribe, your worktree ~/labs/projects/anyscribe-wt/mac-2c-ui on branch feat/mac-app-2c-ui, based on origin/main at 6dc70b2 (includes the onboarding wave and its wizard follow-up). Commit there only, never on main, never push.
- In scope: ui/, src/anyscribe/web/static/ (the rebuilt bundle only), docs/building/. Out of scope: desktop/ (slice 2c-app), the rest of src/, install.sh, install.ps1, pyproject.toml, CHANGELOG.md, BACKLOG.md.
- Install npm packages only inside ui/ in your worktree. Every engine you start uses a throwaway HOME and a free port; stop it by its pid. Headless browsers only.
- Packet: this folder is in your worktree, uncommitted; commit it first and write proof.md here (with checks/ beside it).
- Review target: branch feat/mac-app-2c-ui at 12aa942, diff 6dc70b2..12aa942 (ui/, the rebuilt bundle in src/anyscribe/web/static, docs).
- Lead evidence at 12aa942: ui lint clean; the lead's own run of checks/check_ui.py --no-shots: 173 passed, 0 failed (proof.md, "Lead's own run"). Screenshots: checks/shots (the builder's, 177).
- The app side it calls: feat/mac-app-2c-app at 70e911f (read-only, ~/labs/projects/anyscribe-wt/mac-2c-app; its desktop/README.md is the bridge's real contract).
