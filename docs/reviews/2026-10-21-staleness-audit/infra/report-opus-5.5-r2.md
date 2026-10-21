FIT REVIEW: PR #16 (audit/infra), round 2, head 52ef77f. Reviewer: Opus 5.5, effort high (Claude lane).

VERDICT: CONDITIONAL on (1) CI green on 52ef77f incl. 3.14 and v7 actions; (2) merge order: #16 before or with #19, since #19's whats-automated.md describes the 9-step publish workflow that only exists in this PR. Every round-1 finding fixed for real; no regression; three nits, none blocking.

EARLIER FINDINGS: Astra I1/Opus I2 FIXED (install.sh:352-368; simulated pipx stub with a space in the bin dir, pipx failing, binary missing; __main__.py exists so -m works). Astra I2 FIXED (install.sh:309-311 pip check; install_with_pipx verbatim move; fixes fresh Ubuntu). Astra I3 FIXED (lines 334-347; snippet run on 3.11-3.14 and 3.9; fallback branch safe). Astra I4 FIXED (publish.yml:59-66; markdown in [dev]; rehearse-migration safe before build). Opus I1 DECLINED-OK routed to #19 (whats-automated.md:90-99 lists the 9 steps). Box widths FIXED (all 41 columns incl. indent). tests/test_install_sh.py still holds.

NEW: none confirmed.

FINDINGS
I1. nit. CONFIRMED by tracing. install.sh:282: unknown package manager + no pip + no pipx -> `"$PY" -m pip install --user pipx` dies under set -e with raw "No module named pip" (before: friendlier "pip install failed"). Fix: `*) "$PY" -m pip install --user pipx || die "Could not install pipx automatically. Install pip or pipx for $PY (https://pipx.pypa.io), then re-run the installer." ;;`
I2. nit. CONFIRMED by tracing. install.sh:346 vs 416-424: when neither scripts folder holds anyscribe, the hint says "Run it with: $PY -m anyscribe --version" but the green box still says "Next step: anyscribe ui". Fix: add a line telling the user to type "$PY -m anyscribe" wherever the installer says anyscribe.
I3. nit. PLAUSIBLE, pre-existing. install.sh:279 `sudo apt install -y pipx` without `apt update`; fails in a fresh container with an empty index. Fix: `apt) sudo apt update -qq && sudo apt install -y pipx ;;`

ANSWERS: fresh macOS and fresh Ubuntu 24.04 routes both reach a working anyscribe; python/ffmpeg missing unchanged; bin dir with space and missing binary handled; old pipx without `environment --value` falls back to ~/.local/bin; default-vs-user scheme folder printed correctly (stale double copy too rare to act on); no stray scribe; dry-run always prints the pip route (cosmetic, pre-existing).

PENDING OWNER CHECKS: install.sh goes live on merge (curl from main); pins reach users at the next release; merge order #16 then #19.

NOT RUN: CI; pwsh parse; snippet on a real 3.10; fresh-machine run. INSPECTED: brief, both r1 reports, ledger, impl r2, git show 52ef77f, install.sh in full, install.ps1 boxes, publish.yml, ci.yml, rehearse-migration.sh, pyproject, __main__.py, tests/test_install_sh.py, docs/README/skill/landing installer claims, #19's whats-automated.md. Probes: sysconfig snippet on 3.9, 3.11-3.14; bash -n; bash array simulation; box-width measurement.
