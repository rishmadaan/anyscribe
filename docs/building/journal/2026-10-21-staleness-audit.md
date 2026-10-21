---
type: audit
tags: [docs, skill, building-docs, infra, ci, staleness, audit]
tldr: "Read-only four-area staleness audit at v0.16.5 (HEAD b3cddc1): ~150 findings across user docs, skill, building docs and infra, fixed in five PRs; two decisions left to the owner (a JavaScript runtime for yt-dlp, dropping Python 3.10)."
---

# Staleness audit, 2026-10-21

## What was audited

Four independent read-only audits ran against HEAD `b3cddc1` (v0.16.5), each
checking one area's claims against the code rather than against other docs:

1. **User docs**: `README.md`, `docs/user/`, `landing/`, install scripts.
2. **Skill**: `src/anyscribe/skill/` (SKILL.md + references/).
3. **Building docs**: `CLAUDE.md`, `AGENTS.md`, `docs/building/`, `BACKLOG.md`.
4. **Infra**: versions, dependency pins, CI, release scripts, licensing.

Roughly 150 findings in total. The pattern: the code moved through 0.13 to
0.16 (rename, local files, Groq, MCP v2, docs pipeline, autostart toggle) and
the prose describing it was updated on the user-facing side, which CI gates,
but drifted on the developer side, which nothing gates.

## How the fixes are grouped

Five PRs, one per area, so each can be reviewed against a single audit:

1. User docs + landing.
2. Skill + CLI help text.
3. Building docs + BACKLOG (this entry ships with it).
4. Installers + CI + dependency pins.
5. UI dependency refresh.

## Gap found in the gates

`scripts/check-docs.py` scans only `docs/user`, `landing`, `README.md` and
`src/anyscribe/skill` for stale version strings. Install scripts,
`CONTRIBUTING.md`, `AGENTS.md` and `docs/building/ops` are not scanned and
need a manual grep at release time; `COMMIT_CHECKLIST.md` now says so.

## Decisions left to the owner

- **JavaScript runtime for yt-dlp.** Current yt-dlp wants a JavaScript runtime
  such as Deno for full YouTube support. Verified: without Deno on PATH,
  yt-dlp warns "No supported JavaScript runtime could be found ... some
  formats may be missing". Options are to document it, have the installers
  offer Deno, or accept the reduced format set. Not decided.
- **Python 3.10.** It reached end of life on 2026-10-01. `pyproject.toml`
  still declares `>=3.10` and CI tests 3.10. Dropping it is a support-policy
  call, not a doc fix. Not decided.
