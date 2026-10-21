# Review log: anyscribe staleness audit PRs, 2026-10-21

Size L (PR merge gate). Correctness reviewer: gpt-6-astra, effort high, Codex lane (run folder outside git). Fit reviewer: Opus 5.5, effort high, Claude lane (inherits this session's instruction files and hooks; read-only by instruction).

| Round | PR | Role | Model, effort | Target (sha) | Verdict | Findings |
|---|---|---|---|---|---|---|
| 1 | #15 ui-deps | correctness | gpt-6-astra, high | 0ad9f61 | CONDITIONAL on CI | 1 nit (impl report wording) |
| 1 | #15 ui-deps | fit | Opus 5.5, high | 0ad9f61 | CONDITIONAL on CI | 1 nit (PR description) |
| 1 | #16 infra | correctness | gpt-6-astra, high | 981a7eb | NOT YET | 4 should-fix (pipx launch, no-pip route, PATH hint, publish gates) |
| 1 | #16 infra | fit | Opus 5.5, high | 981a7eb | CONDITIONAL | 1 should-fix (building docs), 2 nits (pipx launch, box widths) |
| 1 | #17 user-docs | correctness | gpt-6-astra, high | e5e33ea | NOT YET | 14 should-fix, 2 nits |
| 1 | #17 user-docs | fit | Opus 5.5, high | e5e33ea | CONDITIONAL | 1 should-fix (landing card), 4 nits |
| 1 | #18 skill | correctness | gpt-6-astra, high | 0b90724 | NOT YET | 9 should-fix, 2 nits |
| 1 | #18 skill | fit | Opus 5.5, high | 0b90724 | CONDITIONAL | 3 should-fix, 3 nits |
| 1 | #19 building-docs | correctness | gpt-6-astra, high | d34ae8a | NOT YET | 4 should-fix |
| 1 | #19 building-docs | fit | Opus 5.5, high | d34ae8a | CONDITIONAL | 6 should-fix, 4 nits |

PR #15 merged as 0bafa4d after CI (frontend rebuild and bundle diff) passed on 0ad9f61; both reviewers' only condition.
| 2 | #16 infra | correctness | gpt-6-astra, high | 52ef77f | NOT YET | all r1 fixed; 1 new should-fix (skipped launch still printed "ready") |
| 2 | #16 infra | fit | Opus 5.5, high | 52ef77f | CONDITIONAL | all r1 fixed; 3 nits |
| 3 | #16 infra | correctness | gpt-6-astra, high | e4fd070 | CONDITIONAL on CI | all r2 fixed; none new |
| 3 | #16 infra | fit | Opus 5.5, high | e4fd070 | GOOD TO GO | 2 optional nits, declined as follow-ups |
| 2 | #19 building-docs | correctness | gpt-6-astra, high | 198758d | NOT YET | all r1 fixed; 1 new should-fix (publish failure overclaim), 3 pre-existing should-fix |
| 2 | #19 building-docs | fit | Opus 5.5, high | 198758d | CONDITIONAL | all r1 fixed; merge-order condition (#16 first), 6 nits |
| 2 | #18 skill | correctness | gpt-6-astra, high | 44fec4c | NOT YET | 9 of 11 r1 fixed, 2 partly; 3 should-fix, 1 nit |
| 2 | #18 skill | fit | Opus 5.5, high | 44fec4c | CONDITIONAL | all r1 fixed; 1 should-fix (per-word timestamp claims), 5 nits |

PR #16 merged after round 3 (CI green on e4fd070; both reviewers' conditions met). Declined follow-ups from round 3 fit: `apt update -qq || true` (kept the fail-loud pattern already used at install.sh:176) and the pipx fallback die() wording.
| 2 | #17 user-docs | correctness | gpt-6-astra, high | 53b864b | NOT YET | 9 of 16 r1 fixed, 7 partly; 5 should-fix, 2 nits |
| 2 | #17 user-docs | fit | Opus 5.5, high | 53b864b | CONDITIONAL on CI | all r1 fixed; fresh-render check passed; 6 nits |
| 3 | #19 building-docs | correctness | gpt-6-astra, high | 5ed32bd | CONDITIONAL on #16 first + CI | all r2 fixed; 1 nit (COMMIT_CHECKLIST version-check wording) |
| 3 | #19 building-docs | fit | Opus 5.5, high | 5ed32bd | GOOD TO GO | 3 nits |
| 4 | #19 building-docs | fit | Opus 5.5, high | 6d6c45c | GOOD TO GO | none (narrow re-check of 4 lead-applied nit lines) |
| 3 | #18 skill | correctness | gpt-6-astra, high | 5298f43 | NOT YET | 1 partly (decision-table cell); 3 should-fix, 1 nit |
| 3 | #18 skill | fit | Opus 5.5, high | 5298f43 | CONDITIONAL | 1 partly (same cell); 2 should-fix, 3 nits |
| 4 | #19 building-docs | correctness | gpt-6-astra, high | 6d6c45c | CONDITIONAL on CI | none new; all r3 nits confirmed fixed |

PR #19 merged after round 4 (CI green on 6d6c45c, incl. 3.14; both reviewers passed it; #16 merged first as required).
| 3 | #17 user-docs | correctness | gpt-6-astra, high | 396d912 | NOT YET | 2 partly (planned-vs-used model, Groq picker promises); 2 should-fix |
| 3 | #17 user-docs | fit | Opus 5.5, high | 396d912 | CONDITIONAL | 1 partly; 2 should-fix (one pre-existing rm example), 4 nits; fresh render EQUAL |
| 4 | #18 skill | fit | Opus 5.5, high | 6823958 | GOOD TO GO | 3 non-blocking nits |
| 4 | #18 skill | correctness | gpt-6-astra, high | 6823958 | NOT YET | all r3 fixed (one partly); 2 should-fix text items (retry hints keep -m; Next-run section ignores the diarize override) |
| 4 | #17 user-docs | correctness | gpt-6-astra, high | f83851e | CONDITIONAL on CI | all r3 fixed; none new; fresh render byte-equal |
| 4 | #17 user-docs | fit | Opus 5.5, high | f83851e | GOOD TO GO | 2 optional nits, declined as follow-ups (first attempt hit the Claude session limit; resumed after the reset) |

PR #18: round 4 is the cap. Astra's two remaining text findings were applied by the lead in 8859dd8 (openai.py and groq.py retry hints; troubleshooting Next-run section) and are UNREVIEWED by any reviewer. pytest 485 passed, ruff and check-docs clean on that commit.

## Outcome

| PR | Rounds | Merged as | Unreviewed fixes |
|---|---|---|---|
| #15 ui-deps | 1 | 0bafa4d | none |
| #16 infra | 3 | 0f3df6b | none (2 nits declined) |
| #19 building-docs | 4 | df26152 | none |
| #18 skill | 4 (cap) | e672b1e | 8859dd8: openai.py and groq.py retry hints, troubleshooting Next-run section (lead-applied after the cap) |
| #17 user-docs | 4 (cap) | 4f12588 | none (2 nits declined) |

All five merged 2026-10-21/22 with CI green on each final head. The record folder docs/reviews/2026-10-21-staleness-audit/ was committed directly to main after the merges (record only, no code).

