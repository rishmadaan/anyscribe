FIT REVIEW: PR #19 (audit/building-docs, d34ae8a), round 1. Reviewer: Opus 5.5, effort high (Claude lane, ran with this session's instruction files and hooks).

VERDICT: CONDITIONAL on CI green on d34ae8a and B1, B2 fixed before merge (journal wording errors in an append-only file); B3 to B6 cheap, same round. Right job, right tool; docs and comments only (languages.py identical with docstring removed); no file overlap with the other PRs.

FINDINGS
B1. should-fix. CONFIRMED. Journal lines 19-22 state the wrong lesson (user docs safe because CI gates them). User-docs audit had 42 findings incl. high ones; skill 39 (4 HIGH); CI gates check version strings, HTML freshness, MCP names, CHANGELOG heading, never commands/flags/JSON shapes. Replacement text supplied.
B2. should-fix. CONFIRMED. tldr, body "fixed in five PRs", "Five PRs, one per area", _index row: says fixed before review/merge; four areas, five PRs. Fix: "filed as five PRs for review"; "one per audit area, except that the infra audit's frontend-dependency finding got its own PR"; add PR numbers.
B3. should-fix. CONFIRMED. providers.md:92 "Deepgram handles large files natively" and the Deepgram section never mentions chunking (deepgram.py:89-102 chunks over 25 MB/30 min; labels not matched across pieces). Replacement text supplied. Same claim in core/quality.py:23, providers/openai.py:111-114 (runtime string), core/resolve.py:58 (skill PR edits it).
B4. should-fix. CONFIRMED. CLAUDE.md step 5 and languages.py rule name only one hardcoded nova spot; core/resolve.py:115-116 also hardcodes hi-latn for the run-line note. Fix: name both (_build_params in deepgram.py and the run-line note in resolve.py).
B5. should-fix. CONFIRMED. providers.md new Groq bullet records a real user-facing gap (no groq entry in PROVIDER_LANGUAGES; routes/config.py returns []) as if intended. Append "(a gap, not a design choice: Groq runs Whisper; tracked in BACKLOG)" and add a BACKLOG line. No code change.
B6. should-fix. PLAUSIBLE. BACKLOG shim checkbox evidence does not cover the re-declared entry points. (Lead verified the wheel: ascli, scribe, scribe-mcp all declared.)
B7. nit. PLAUSIBLE. Journal "Python 3.10 reached end of life on 2026-10-01": python.org gives a month. (Lead: endoflife.date lists 2026-10-01; reword to October 2026 with the source.)
B8. nit. CONFIRMED. web/routes/config.py:182 comment repeats the false "router reads the list" claim. Comment-only fix.
B9. nit. CONFIRMED. COMMIT_CHECKLIST "2b. [ ]" / "2c. [ ]" are not list markers; render run together.
B10. nit. CONFIRMED. New line-number citations (settings.py:49, local.py:30, sargam.py:29, :148, deepgram.py:47) will drift; cite symbols.

Checked correct: every Architecture tree path exists; PROVIDER_* registration points exist; can_handle on all three downloaders, DOWNLOADERS order; deepgram.py:47 hardcodes {"hi-latn"}; SARVAM_MAX_DURATION 28; no with_diarization; turns parsed; REST list matches every decorator; matrix rows (autostart darwin-only, pystray; migrate registered; migrate_app_home_once called from paths.py and settings.py); BACKLOG table 58 rows ascending, every tag has a row, new rows match tag dates; vercel.json exists, pages.yml deleted in 149032f; [tray] extra and pidfile; _index newest-first, 51 journal files, links resolve; CI facts match; check-docs scope sentence accurate; yt-dlp sentence quotes the verified warning; Windows in AGENTS.md matches.

ADVICE: hand-written REST list will drift again; acceptable while routes/*.py is named as source of truth. Repo keeps two divergent instruction files (CLAUDE.md full, AGENTS.md pointing at it) against the owner's doctrine (AGENTS.md single source, one-line CLAUDE.md); a future PR could fold them. Not a defect here.

PENDING OWNER CHECKS: whether to fix the Groq language list in a patch release; the two settled decisions.

NOT RUN: CI; wheel entry points (lead ran it); EOL date (lead ran it); pytest/ruff/build. INSPECTED: brief, full diff, all 60 audit items, impl report, other audits' headers, other PR diffs' file lists; CLAUDE.md, AGENTS.md, BACKLOG.md, docs/building/{_index,providers,architecture,COMMIT_CHECKLIST}.md, ops/{pypi-guide,release-checklist}.md; providers/*, downloaders/*, core/{resolve,quality,migrate,tray}.py, config/{paths,settings}.py, cli/main.py, web/routes/*.py, web/models.py, scripts/check-docs.py, workflows, pyproject.toml, tests/ names, git tag dates.
