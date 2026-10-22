(Opus 5.5, effort high, fit reviewer, round 4, target ce39489. Verdict: CONDITIONAL on I1 to I4, CI green on the fix commit, Docker upgrade re-run after I2.)

Round-3 ledger: all FIXED (Astra I1/Opus I1, Astra I2, Astra I3 for the tested case, Astra I4/Opus I2 except one word, Opus I4, I5, I6); Opus I3 PARTLY; real-machine runs DECLINED-OK.

I1 should-fix CONFIRMED install.sh:346,348,351: the three version substitutions are plain assignments under set -e; a dead old `anyscribe` first on PATH (exit 126) makes the installer exit silently after a successful install. Fix: `|| true` inside each substitution.
I2 should-fix PLAUSIBLE install.sh:300-303: the `pipx list | grep` guard can be false under pipefail or with a broken venv, skipping the uninstall and keeping the old Python. Fix: do not parse; uninstall unconditionally (or check the venv dir).
I3 should-fix CONFIRMED CHANGELOG:51: "migrate alone does not" refresh the skill is false; migrate installs the skill itself (migrate_cmd.py:264-276). Use "migrate --dry-run".
I4 should-fix CONFIRMED SKILL.md:30 and skill troubleshooting: they point to "the one-line installer" without giving the command; pip install fails on externally managed Pythons. Give the curl/irm commands, tell Claude not to run them, use doctor's Python row in troubleshooting.
N1 nit getting-started Linux block hardcodes /usr/bin/python3.11 (not on Ubuntu 24.04+). Two labelled blocks.
N2 nit (pre-existing) macOS manual pip fails on Homebrew Python (externally managed); pipx route.
N3 nit PLAUSIBLE install.ps1:179,182: in PowerShell 5.1 with ErrorActionPreference Stop a native command writing stderr under 2>$null throws; wrap the probes in try/catch.
N4 nit shadow warning says "Remove the old one" without how; Windows skips Fix-Path in that branch.
Answers: pipx_bin_dir order fine; grep pattern fine except pipefail/broken venvs; no-separate-yt-dlp claim true (deps.py always uses python -m yt_dlp; installer still apt-installs yt-dlp needlessly, side note); check-docs 0 offenders at 0.17.0; release.sh needs the review folder committed and tomllib (3.11+).
Pending owner: one real Windows run and one Mac with a python.org 3.10 first on PATH, after publishing.
