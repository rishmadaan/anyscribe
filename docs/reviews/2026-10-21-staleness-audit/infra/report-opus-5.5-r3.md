FIT REVIEW: PR #16 (audit/infra), round 3, head e4fd070. Reviewer: Opus 5.5, effort high (Claude lane).

VERDICT: GOOD TO GO. CI passed on this exact SHA (run 39644867020: docs, frontend, python 3.10/3.12/3.14). All three claimed fixes are real; probed with the brief's inputs. Two optional nits, no blockers. Round 3 touches only install.sh and its test (+34/-5).

EARLIER: Astra I1 FIXED (empty pipx bin dir: skip message, "(looked for ...)", installed box, "launch you asked for did not run", pipx hint, exit 0, no "ready"; RUN_ONBOARD same; pipx failing same; executable present with DRY_RUN launches then "ready"; no flags: nothing from run_post_install, installed box). Opus I1 FIXED (|| die). Opus I2 DECLINED-OK. Opus I3 FIXED (install.sh:280). New test can fail for the right reason: two in-memory mutations (guard removed; flag never set) both print "ready"; check=True makes a crash a failure; asserts last line is main; CI Linux-only.

NEW
I1. nit. set -e behaviour CONFIRMED, apt exit on broken repo PLAUSIBLE. install.sh:280 `sudo apt update -qq && sudo apt install -y pipx`: in a case arm under set -e a failed left side of && does not abort, so a dead PPA skips the install and pipx later dies with "command not found". Fix: `sudo apt update -qq || true; sudo apt install -y pipx`.
I2. nit. CONFIRMED. install.sh:283 die text says "Install pip or pipx for $PY"; on apk/zypper/emerge distros with externally managed Python, installing pip is the wrong advice. Fix: "Install pipx with your system package manager (see https://pipx.pypa.io), then re-run the installer."

ANSWERS: each concrete input behaves as specified; bash -n passes on bash 3.2.57; no docs reference the old or new installer message text.

PENDING OWNER CHECKS: optional real fresh Linux run of the apt and unknown-package-manager paths.

NOT RUN: pytest and ruff (CI ran both and passed). Disclosure: two read-only gh API calls to confirm CI on the exact SHA. INSPECTED: brief-r3, impl r3, git show e4fd070, install.sh in full, tests/test_install_sh.py, ci.yml, diff stats, git diff --check. Not re-checked this round: pins, action tags, install.ps1 (unchanged since round 2).
