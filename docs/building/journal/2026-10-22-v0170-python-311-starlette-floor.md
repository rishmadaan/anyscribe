---
type: decision
tags: [release, python, dependencies, security, starlette, fastapi]
tldr: "v0.17.0 drops Python 3.10 (end of life October 2026) and adds a direct starlette>=1.3.1 floor with fastapi>=0.133; this settles three of the four questions put to the owner after the 2026-10-21 audit (cut a release, drop 3.10, add the floor); the yt-dlp JavaScript runtime stays open."
---

# v0.17.0: Python 3.11 floor and Starlette floor

## What changed

- `requires-python` is `>=3.11`. The 3.10 classifier is gone, CI tests 3.11,
  3.12 and 3.14, and every place that told a user "3.10+" (install.sh,
  install.ps1, `anyscribe doctor`, README, getting-started, landing) says
  3.11+. The installer's candidate list is now `python3.13 python3.12
  python3.11 python3`.
- `starlette>=1.3.1` is a direct dependency, with `fastapi>=0.133`.

## Why

Python 3.10 reached end of life in October 2026. Dropping it is a minor bump
(0.16.x to 0.17.0) because it is breaking for 3.10 machines; pip's
`requires-python` check keeps them on 0.16.5 rather than installing something
that cannot run.

The PR #16 review established that raising the FastAPI floor does not fix the
Starlette advisories: fastapi 0.110 pins `starlette<0.37`, 0.115 pins `<0.39`,
0.132 still pins `<1.0.0`, and OSV lists advisories against every Starlette in
those ranges. FastAPI's current pin (`starlette>=0.46.0`) still permits those
versions; only a direct floor excludes them. The first FastAPI release whose
pin admits 1.3.1 is 0.133.0, so the floor pair is `fastapi>=0.133` plus
`starlette>=1.3.1` (released 2026-06-12, Python >=3.10; OSV lists two
advisories against 1.3.0 and none against 1.3.1). Checked against the PyPI
JSON and the OSV API for each version on 2026-10-22.

## Decided by the owner, 2026-10-22

Asked after the audit: cut a release (yes), drop 3.10 (yes, before release),
add the Starlette floor (yes, before release). The yt-dlp JavaScript runtime
question stays open; upstream's EJS page recommends Deno (minimum 2.3.0), also
accepts Node 22+ behind `--js-runtimes node`, and `yt-dlp[default]` adds only
the challenge scripts (`yt-dlp-ejs`), which still need a runtime to run.
