# Fit review, round 4 (cap) (Claude Fable 5.1, Agent tool), target 0382449

Saved by the lead from the reviewer's final message (summary; full text in the session transcript).

VERDICT: GOOD TO GO. All four round-3 fixes real (F1 Linux /proc cmdline + ps -ww; F2 Windows skipif; F3 port check unconditional, bare open defaults to the installed port; F4 journal correction; F6 architecture clause; F5 DECLINED-OK); each survives the brief's break attempts (empty/unreadable/vanished /proc entries, dead pid on macOS, equal port with no tray, no manifest and no plist, manifest without plist, reinstall 8457 → 9000); tests assert identity with mutation evidence; fixtures never touch the real ~/.anyscribe; CI 39815726235 green in all seven jobs. Live probes on this Mac consistent (tray 66259, server 66261, health app=anyscribe, installed_port 8457).

Nits (doc-only, non-blocking): F1 journal line 144 says "since the r1b fix" (a review-round codename unresolvable later); F2 `uninstall()`/`status()` take the port from the manifest or 8457 while `open` uses the login item too (reporting inconsistency in the already-accepted "Partly installed" state).

Pending owner checks: Linux end-to-end with a long pipx/uv path (stranger test running); Windows double-click (deferred).
