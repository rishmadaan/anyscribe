# Implementer report: audit/building-docs (commit d34ae8a)

Worktree: <checkout>

16 files, 204+, 119-: AGENTS.md 9, BACKLOG.md 54, CLAUDE.md 39, docs/building/COMMIT_CHECKLIST.md 15, _index.md 7, architecture.md 41, downloaders.md 12, journal/2026-10-21-staleness-audit.md 50 (new), ops/pypi-guide.md 2, ops/release-checklist.md 30, ops/whats-automated.md 23, plans/rename-to-anyscribe.md 4, plans/v0.1.0-original-plan.md 2, providers.md 23, web-ui-spec.md 2, src/anyscribe/providers/languages.py 10 (comments only).

Checks: pytest 484 passed, 1 skipped; ruff check src passed; check-docs.py exit 0.

Applied: all 60 (47 and 60 trivial, done). Wording differences: #1 added "(unless marked <!-- version-pin-ok -->)"; #4 CLAUDE.md per spec, languages.py only the two comments rewritten, deepgram.py untouched; #19 cites migrate_app_home_once by name (the per-read entry point called from config/paths.py and config/settings.py); #43/#44 release-checklist steps renumbered 5 to 8, GitHub Release is step 6, fixed the "(step 9)" cross-reference. check-docs scope line added to COMMIT_CHECKLIST under "After version bumps". Journal entry 50 lines, type: audit, row at top of _index.md.

Declined: none.

anyscribecli PyPI (#53): 0.15.2 live, uploaded 2026-07-31T11:14:42, summary "Renamed to anyscribe. Install that instead", requires_dist ['anyscribe>=0.16.0']. Shim checkbox ticked with that evidence inline. Wheel entry points not opened.

Missed by audit, fixed here: architecture.md said Sarvam chunks at 30 s in two more places (provider-layer and core-layer bullets), now 28 s; providers.md separate line "28s chunks mean speaker IDs may restart" removed with the diarization bullet; whats-automated "Version sync check" row now says what is already covered.

Not fixed (outside scope): src/anyscribe/web/routes/config.py:182 comment `e.g. "model" for Deepgram routing` repeats the false router claim; whats-automated "Future Automation Candidates" still lists "Changelog generation" though the 2026-08-09 journal decided against it.

Not done: old journal bodies not read; 0.15.2 wheel not opened.
