---
type: audit
tags: [docs, skill, building-docs, infra, ci, staleness, audit]
tldr: "Read-only four-area staleness audit at v0.16.5 (HEAD b3cddc1): ~150 findings across user docs, skill, building docs and infra, filed as five PRs for review; two decisions left to the owner (a JavaScript runtime for yt-dlp, dropping Python 3.10)."
---

# Staleness audit, 2026-10-21

## What was audited

Four independent read-only audits ran against HEAD `b3cddc1` (v0.16.5), each
checking one area's claims against the code rather than against other docs:

1. **User docs**: `README.md`, `docs/user/`, `landing/`, install scripts.
2. **Skill**: `src/anyscribe/skill/` (SKILL.md + references/).
3. **Building docs**: `CLAUDE.md`, `AGENTS.md`, `docs/building/`, `BACKLOG.md`.
4. **Infra**: versions, dependency pins, CI, release scripts, licensing.

Roughly 150 findings in total (building docs 60, user docs 42, skill 39,
infra 10). The code moved through 0.13 to 0.16 (rename, local files, Groq,
MCP v2, docs pipeline, autostart toggle) faster than the prose. CI's docs
gates catch stale version strings, unrendered HTML, a missing MCP tool name
and a missing CHANGELOG heading; none of them checks that a documented
command, flag or JSON shape matches the code. So the user docs and the skill
drifted too (wrong --json shape, `anyscribe --clipboard` failing), and the
developer docs, which nothing gates, drifted most.

## How the fixes are grouped

Five PRs, one per audit area, except that the infra audit's
frontend-dependency finding got its own PR, so each can be reviewed against a
single audit:

1. #15 UI dependency refresh (merged 2026-10-21).
2. #16 Installers + CI + dependency pins.
3. #17 User docs + landing.
4. #18 Skill + CLI strings.
5. #19 Building docs + BACKLOG (this entry ships with it).

## Infra changes in #16

beaupy is capped below 4: 4.0.1 (2026-10-15) makes Ctrl+C raise where the
onboarding wizard expects `None`. CI tests Python 3.10, 3.12 and 3.14, and
3.14 is now classified; 3.15 is held until ctranslate2 ships cp315 wheels.
The python-multipart floor is 0.0.31. The fastapi floor bump was declined
because no fastapi floor reaches a Starlette without known advisories; a
direct starlette floor is the owner's call. The publish workflow now runs the
same gates as CI before it uploads anything.

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
- **Python 3.10.** It reached end of life in October 2026 (endoflife.date lists 2026-10-01). `pyproject.toml`
  still declares `>=3.10` and CI tests 3.10. Dropping it is a support-policy
  call, not a doc fix. Not decided.
