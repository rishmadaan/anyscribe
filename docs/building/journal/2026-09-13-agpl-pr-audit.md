---
type: troubleshooting
tags: [licensing, review, packaging, skill, windows]
tldr: "Claude audited PR #14 read-only; fixed encoding, dashboard copyright, release-boundary copy, and independently verified standalone skill licensing."
---

# Read-only audit of AGPL PR #14

Created [PR #14](https://github.com/rishmadaan/anyscribe/pull/14) from
`codex/agpl-license`, initially at `fdacb79`. User requested `claude -p` to audit
the PR without modifying it, then asked Codex to fix confirmed findings.

Claude ran with `--permission-mode plan`, `--tools Read,Glob,Grep`, the same
`--allowedTools` list, `--strict-mcp-config`, `--disable-slash-commands`, and
`--no-session-persistence`. It received the PR metadata and diff plus access to
repository files. Shell/edit/GitHub-write tools were unavailable. Its structured
result reported success, 22 turns, and no permission denials. No repository
changes were made by the reviewer. The invocation used an empty stdin pipeline
and streaming JSON so progress could be observed; the initial non-streaming
attempt was restarted after producing no audit output.

## Findings and fixes

- **Corrupted BACKLOG heading:** the new heading contained a literal `?` instead
  of an em dash. Corrected using a UTF-8-preserving edit.
- **Dashboard copyright:** added an in-app copyright line above the existing
  AGPL/no-warranty link. Rebuilt the committed frontend.
- **Landing release boundary:** added an explicit statement that AGPL applies
  to the next package release and previous MIT copies retain their permissions.
- **Getting-started ordering:** moved legal guidance after setup instructions.
  Regenerated the user-doc HTML.
- **Standalone skill distribution (Codex follow-up):** tracing
  `copy_skill_files()` showed it only copied the guide and references. Added the
  complete license to the bundled skill, a grant/copyright notice in its guide,
  and copying of the license during installation. Explicit UTF-8 reads/writes
  preserve the guide/reference text on Windows. All installation call sites
  converge on this function; no new installer or configuration was added.

The reviewer found the main license text, compound SPDX expression, packaged
notices, source inclusion, existing static-serving path, and CI gates coherent.
Its cosmetic inline-separator suggestion was not changed: the rendered links
were acceptable and the separator is unrelated to the compliance fixes.

## Verification

The new skill tests were observed failing with the missing bundled license,
then passing with the complete text present. They compare it with the root
license and verify the installed copyright/grant, full text, and reference
contents. They pass even without Python UTF-8 mode, verifying the installer's
explicit encoding handling. Python/frontend lint, frontend rebuild, and docs
render/drift checks passed. No dependency versions were changed.

All 61 focused skill/web tests passed. Wheel and sdist builds and Twine checks
passed; artifact inspection confirmed the standalone skill's full license and
copyright/grant are included.

The initial PR passed all remote checks: Python 3.10/3.12, frontend, docs, and
Vercel preview. Package release, version bump, and merge remain outside this PR
creation/audit task. Existing Windows-wide test limitations are documented in
the [adoption journal](2026-09-13-agpl-license-adoption.md).
