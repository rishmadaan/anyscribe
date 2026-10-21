# Implementer report, round 3 fix: audit/infra commit e4fd070 (parent 52ef77f)

Files: install.sh, tests/test_install_sh.py.

1. Astra I1 FIXED. New global POST_INSTALL_SKIPPED=false. When the pipx executable is missing, run_post_install prints "Automatic launch skipped: the anyscribe executable could not be found. Run `pipx list` to inspect the installation." followed by "(looked for <path>)", sets the flag, returns 0. main prints the "ready" box only when the flag is not set; otherwise the "installed" box plus "anyscribe was installed, but the launch you asked for did not run (see above)." then the existing pipx PATH hint. Exit code stays 0.
2. Opus I1 FIXED. Unknown-package-manager fallback: `"$PY" -m pip install --user pipx || die "Could not install pipx automatically. Install pip or pipx for $PY (https://pipx.pypa.io), then re-run the installer."`
3. Opus I3 FIXED. apt line: `sudo apt update -qq && sudo apt install -y pipx`.

Regression test test_skipped_pipx_launch_does_not_claim_ready in tests/test_install_sh.py (22 lines): evals install.sh minus its final `main` line (bash 3.2 cannot source <(...)), stubs brew/python/yt-dlp/ffmpeg and the install step (sets USED_PIPX=true), command_exists always returns 1, pipx echoes an empty tmp dir, RUN_UI=true, calls main, asserts "Automatic launch skipped" present and "anyscribe is ready!" absent; also asserts the script's last line is `main`. Mutation: with the banner condition reverted, 1 failed ("assert 'anyscribe is ready!' not in ..."); restored, 1 passed.

Checks: bash -n ok; tests/test_install_sh.py 6 passed; full suite 485 passed, 1 skipped; ruff all passed; git diff --check clean; box lines untouched.

Not checked: real Linux apt/dnf/unknown runs (inspection and syntax only).
