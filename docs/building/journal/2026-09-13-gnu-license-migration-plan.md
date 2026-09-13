---
type: research
tags: [licensing, release, packaging, planning]
tldr: "Plan the MIT-to-GNU migration: choose GPLv3 or AGPLv3, establish provenance, preserve notices, verify source distribution, then release. Not implemented."
---

# GNU license migration plan

Status: proposal only. No license, application, package metadata, or release has been changed.

## 1. Choose the exact license

Planning default: **GPL-3.0-or-later** for the existing local application. This permits recipients to use GPL version 3 or a later FSF version. Choose **GPL-3.0-only** instead if future license versions should require a deliberate maintainer decision.

| Choice | Intended outcome |
| --- | --- |
| GPL-3.0-or-later | Copyleft for distributed copies and covered derivative works; corresponding source must be supplied as required by the license. |
| AGPL-3.0-or-later | GPL-style distribution obligations plus a source offer to remote users interacting with modified network versions. |
| LGPL-3.0-or-later | Weaker copyleft suited to libraries that should permit proprietary linking; not the proposed choice for this application. |

The existing [hosted MCP plan](2026-07-31-hosted-mcp-connector-plan.md) makes AGPL a meaningful alternative. Choose AGPL if keeping modified hosted forks open is a goal. Merely calling external transcription APIs does not require choosing AGPL.

Both GPL and AGPL permit commercial use and charging money. Neither prevents competition or requires every private edit to be published. They do not automatically license user transcripts or input media under the program's license. Do not add noncommercial or no-SaaS restrictions to the standard GNU text.

Sources: [GNU license recommendations](https://www.gnu.org/licenses/license-recommendations.en.html), [GNU FAQ](https://www.gnu.org/licenses/gpl-faq.en.html), [AGPL rationale](https://www.gnu.org/licenses/why-affero-gpl.html), [version selection](https://www.gnu.org/licenses/identify-licenses-clearly.html).

Decision needed before implementation: GPL or AGPL, and only versus or-later. No assumption in this proposal constitutes an adopted license.

## 2. Establish ownership and the release boundary

Observed state:

- Root `LICENSE`: MIT, copyright 2026 Rishabh Madaan.
- `pyproject.toml`: version 0.16.4, MIT expression and MIT Trove classifier.
- README: MIT badge and license section.
- `landing/index.html`: six MIT references.
- `ui/package.json`: private frontend package with no license field.
- Git author summary: three author identities appearing to belong to the maintainer. This is evidence to review, not proof of ownership; copied code, coauthors, and employment rights are not established by commit counts.

Implementation checklist:

1. Review commit/coauthor history and copied source, documentation, icons, fonts, images, and bundled skill files. Confirm rights to apply the chosen license to first-party material.
2. Preserve existing third-party notices. MIT contributions can generally be incorporated into a GPL-covered whole while keeping their required MIT notices; do not claim their original permissions disappeared. Obtain permission or replace material only where existing grants are insufficient.
3. Record the first GNU-licensed release and its exact commit. Propose 0.16.5 if still available, consistent with this repository's patch-release preference; recheck the version at implementation time.
4. Preserve old tags and PyPI artifacts. Earlier MIT copies retain MIT permissions, and others can continue forks from them. The migration affects the new release and subsequent covered changes; it cannot retroactively revoke those grants.

Exit condition: ownership/provenance uncertainties are resolved and the license/release boundary is written down.

## 3. Audit the actual distributed dependencies

Produce a small table in the implementation journal: component, resolved version, authoritative license, how it is used/distributed, required notices/source, and resolution of any incompatibility.

- Review Python core dependencies plus `local`, `mcp`, and `tray` extras and their transitive dependencies, including platform-specific packages.
- Review exact frontend versions from `ui/package-lock.json`, especially code and assets included in the built bundle. Distinguish build-only tools from shipped material.
- Check yt-dlp distribution variants, FFmpeg builds, native libraries, and downloaded model weights separately. An executable invoked as a separate process, a linked library, and a bundled executable need different analysis. Do not infer a binary's license from the project's name alone.
- Separate remote API service terms from the license of code included in anyscribe. Model weights and downloaded media retain their own terms.
- Record the versions audited because Python dependency ranges are open-ended; the result does not certify every future resolution.

This planning pass inventories the scope; it has not completed or certified dependency compatibility. Use [GNU's license compatibility list](https://www.gnu.org/licenses/license-list.html) and each component's actual license files during implementation.

Exit condition: every redistributed component has compatible terms and a concrete notice/source compliance path.

## 4. Apply one focused migration change

| File/surface | Planned change |
| --- | --- |
| `LICENSE` | Install the complete, unmodified official GNU license text selected in step 1. |
| First-party source notices | Retain copyright ownership; add a consistent short license grant/SPDX identifier and reference to `LICENSE` in maintained Python/TypeScript/JavaScript source. Preserve third-party headers; do not hand-edit generated bundles. |
| `pyproject.toml` | Set the exact SPDX expression; remove the deprecated MIT license classifier; explicitly include license/notice files and verify Hatchling support. If bundled components require a compound distribution expression, derive it from the audit rather than blindly labeling every component GPL. |
| `ui/package.json`, `ui/package-lock.json` | Add the selected first-party license and synchronize root package metadata without upgrading dependencies. |
| `README.md` | Update badge and license section; describe the release boundary, commercial use, and third-party exceptions. |
| `landing/index.html` | Replace its six current-license MIT claims with the selected GNU license and link. |
| Third-party notices | Include the attribution/license texts required by the audit in a packaged notice file or directory; preserve emitted bundle notices. |
| Contributor guidance | Add a concise inbound-contribution license statement and requirement to disclose third-party material. No CLA system unless separate commercial licensing is actually intended. |
| `CHANGELOG.md`, `BACKLOG.md` | Clearly announce the license transition in the new release. Preserve historical MIT statements as history. |
| Building docs | Add an implementation decision journal and index row; record the chosen license, provenance findings, dependency results, and release boundary. Follow `COMMIT_CHECKLIST.md`. |

Packaging metadata reference: [PyPA specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/). GNU application guidance: [how to use GNU licenses](https://www.gnu.org/licenses/gpl-howto.en.html).

## 5. Make source and license information available

The wheel ships generated React files from `src/anyscribe/web/static/`. Corresponding source needs the preferred editable frontend source, backend source, and necessary build/configuration files, not just minified JavaScript.

- Inspect wheel and sdist contents. Ensure the sdist or an accompanying same-release source archive includes `ui/src`, frontend manifests/lockfile, Vite/TypeScript configuration, Python source, and necessary build scripts and notices.
- Publish matching source beside downloadable artifacts through a distribution method that satisfies the selected license. Link to the exact release, not a moving `main` branch. Include installation information where the license requires it for any future covered device distribution.
- Review CLI and Web UI legal-notice presentation against GNU requirements. Provide accessible copyright, license/no-warranty information, and source instructions; use a small existing help/About surface where possible.
- If AGPL is chosen, plan a prominent source-download offer for remotely used modified deployments, including the future hosted MCP surface. It must match deployed code and include covered modifications; a generic upstream repository link is insufficient. Do not publish credentials or user data with source.

## 6. Verify, then release

1. Search tracked files for current-license MIT claims. Keep third-party MIT notices and historical journal/release records intact.
2. Build wheel and sdist with `python -m build`; inspect their license files, `License-Expression`, `License-File` entries, and corresponding-source contents. Run `python -m twine check dist/*` on only the new artifacts.
3. Rebuild the frontend and confirm committed static assets match. Verify required notices survived minification and are packaged.
4. Run existing CI gates: Python lint/tests, frontend lint/build, docs rendering and `scripts/check-docs.py`. Add only a small artifact check if needed to keep missing licenses/source from recurring.
5. Install the built wheel in a disposable environment and check version/help, UI, and source/license links. Keep real user configuration untouched.
6. Prepare the release with matching `__init__.py`/`pyproject.toml` versions and all version/checklist updates. Include a plain-English license-change note in the GitHub release rather than relying solely on generated commit notes.
7. Publish only in a separately authorized implementation/release task. Tag pushes trigger `.github/workflows/publish.yml`, which uploads to PyPI and creates a GitHub release; do not use a tag as a rehearsal.
8. Verify public GitHub license detection, PyPI metadata/artifacts, landing-page wording, and exact-version source availability after publication.

Done means: selected license is explicit, provenance and dependency checks are recorded, metadata and public claims agree, required notices/source ship with a working access path, checks pass, and the new release clearly states the MIT-to-GNU boundary.

Estimated execution: one focused migration PR and one release once license choice and provenance are settled. Most uncertainty lies in attribution/source auditing, not changing the license file. No application redesign is required.
