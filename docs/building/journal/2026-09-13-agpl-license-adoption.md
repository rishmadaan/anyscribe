---
type: decision
tags: [licensing, packaging, web, release]
tldr: "Adopt AGPL-3.0-or-later locally, preserve bundled MIT/ISC attribution, and explicitly ship editable UI source; release remains unpublished."
---

# Adopt GNU AGPLv3 or later

Rishabh selected AGPLv3 after discussing hosted-service protection and the
Anyscribe Cloud plan. Implementation uses `AGPL-3.0-or-later`, as stated in the
conversation. This supersedes the GPL default in the earlier
[migration proposal](2026-09-13-gnu-license-migration-plan.md).

## Scope and release boundary

Root `NOTICE` preserves Rishabh Madaan's 2026 copyright and grants the first-party
code, docs, and assets under AGPLv3 or later, except separately licensed material.
`LICENSE` contains the complete AGPL text, retrieved from
[SPDX license-list-data](https://github.com/spdx/license-list-data/blob/main/text/AGPL-3.0-or-later.txt)
after direct GNU text retrieval failed. The wording is not customized.
README, landing copy, frontend metadata, CLI help, dashboard links, and user docs
reflect the new license. A root grant avoids identical header edits across every
source file merely for this migration.

No commit, tag, version bump, push, deployment, or release was made. Changes are
under `Unreleased`; assign a new version before publishing. Local review
artifacts still carry the development tree's 0.16.4 version and must not replace
that existing MIT release. Earlier MIT copies retain their original permissions.

Git history shows three apparent maintainer author identities and AI coauthor
trailers; no additional human coauthor was found. This records repository
evidence, not a certification of employment rights or every asset's origin.
The owner requested the change; third-party notices and grants are retained.

## Packaging and attribution

First-party licensing is **AGPL-3.0-or-later**. Distribution metadata is
`AGPL-3.0-or-later AND MIT AND ISC` because the wheel/sdist contain MIT/ISC
frontend components too. This is not an alternative MIT license for anyscribe.
Removed the obsolete MIT Trove classifier and required Hatchling 1.27+ for
modern license metadata.

Vite's native `build.license` emits `THIRD-PARTY-LICENSES.md` on each build.
Actual bundled JavaScript inventory from the unchanged lockfile:

| Component | Version | Preserved license |
| --- | --- | --- |
| lucide-react | 1.8.0 | ISC plus MIT for Feather-derived icons; both texts retained |
| react | 19.2.5 | MIT |
| react-dom | 19.2.5 | MIT |
| react-router | 7.14.1 | MIT |
| scheduler | 0.27.0 | MIT |

Tailwind CSS and Vite runtime helper MIT notices are copied from their installed
license files into `NOTICE`; JavaScript enumeration does not cover generated CSS
or Vite's own helpers. Fonts remain remotely loaded; no font files were bundled.

Installed Python core metadata was inspected: typer 0.27.2, PyYAML 6.0.3,
rich 15.0.0, beaupy 3.12.0, FastAPI 0.141.1 are MIT; python-dotenv 1.2.3,
httpx 0.28.1, uvicorn 0.52.4 are BSD-3-Clause; yt-dlp 2026.8.19 is Unlicense;
python-multipart 0.0.32 is Apache-2.0. Tests also use MCP 2.2.0 (MIT). Installed
core/MCP transitive metadata includes permissive and MPL-2.0 components. Python
dependencies are installed separately, not vendored in these artifacts. This
does not certify all future resolutions, optional native binaries, model weights,
or dependencies on other platforms. Those retain their own terms.

The sdist explicitly includes editable `ui/`, Python source, scripts, tests and
docs; node_modules, environment files and Python caches are excluded. Both
artifacts include all three license/notice files. Sources:
[PyPA metadata](https://packaging.python.org/en/latest/specifications/pyproject-toml/),
[Vite build.license](https://vite.dev/config/build-options#build-license),
[GNU compatibility list](https://www.gnu.org/licenses/license-list.html).

## Source availability

The dashboard exposes license, Source, and third-party notice links; CLI help
links to license/source information. `CONTRIBUTING.md` documents source builds
and distribution requirements. Upstream publication must include matching source
archives and a Git tag. Modified network deployments must replace the upstream
Source link with their own exact deployed source, including modifications. The
future hosted MCP product needs its own accessible source offer; that service
is not implemented here. Generic upstream links are not asserted to satisfy a
modified third-party deployment's obligations.

## Validation

- Python/frontend lint and frontend build passed; bundle and notices regenerated
  without dependency upgrades.
- Wheel and sdist build passed, including building the wheel from the sdist;
  both passed Twine checks.
- Archive inspection confirmed the compound SPDX expression, all three license
  files, editable UI source/manifests/configuration and Python source, with no
  node_modules, environment files or Python caches.
- Docs render/drift checks passed in Python UTF-8 mode. Existing scripts fail
  with Windows' default cp1252 decoding; no unrelated script changes were made.
- All 59 web smoke/onboarding/local tests passed.
- Installed the built wheel into a disposable target with isolated user paths:
  CLI help, the UI index, and served third-party license notices passed smoke checks.
- The broader Windows run reached 367 passes, 2 skips and 8 failures before
  KeyboardInterrupt in later tests. All eight failures reproduced on a clean
  `git archive HEAD` baseline: first-run output contaminating batch JSON, WSL
  bash receiving a Windows path, POSIX home/path assumptions, a platform-specific
  filesystem error string, and Unix permission assertions on Windows. These
  existing issues were not changed in the licensing work.

Before publishing: assign a fresh version, run the Linux release gates, publish
matching source/binary artifacts, and verify GitHub/PyPI/site license and source
links. See the new licensing section in `COMMIT_CHECKLIST.md`.
