(Opus 5.5, effort high, fit reviewer, round 2, target 6cad090. Verdict: CONDITIONAL on I1, I2, I3.)

Round-1 ledger: all FIXED except Astra I4/Opus I5 PARTLY (three doc hints still say bare yt-dlp). New defects from the fixes: I1 (download.py probes and flags Instagram too), I2 (check_python's first attempt passes "python3 python3-venv" to dnf/pacman as one name; pacman now dies where "python3" used to resolve).

I1 should-fix CONFIRMED cli/download.py:122-130: Instagram video downloads now run up to three --version probes and get --js-runtimes; brief lists Instagram behaviour change as must-never. Fix: look up the runtime only when platform == "youtube".
I2 should-fix CONFIRMED (dnf) / PLAUSIBLE (pacman) install.sh:233: make step 1 per manager (apt: "python3 python3-venv"; others: "python3"); add a CHANGELOG Fixed line for the Linux installer change.
I3 should-fix PLAUSIBLE docs/user/troubleshooting.md:185, skill troubleshooting:95,:139: hints still say pip install --upgrade yt-dlp; yt-dlp rejects a mismatched yt-dlp-ejs and its vendored fallback needs npm access, which Node cannot do. Use "yt-dlp[default]" in all three.
I4 nit: journal line 34 (download.py also passes the flag), journal bullet on stderr/auto-update/health, BACKLOG and downloaders.md mention of cli/download.py, CHANGELOG Fixed line "auto-update messages no longer appear in --json output".
I5 nit: getting-started winget two packages in one call (older winget takes one); troubleshooting block mixes three OSes, split into labelled blocks.
Answers: probe parses deno/node banners correctly; stderr-only deno accepted; hung binary 10 s per candidate; Windows colon split safe; one warning per process; nothing treats stderr as failure; health ok correct; install.sh guards hold; macOS without brew reaches curl only after the brew install itself failed; check_python on 22.04 and Debian 12 fine; script(1) -qec supported on ubuntu-latest.
Pending owner: nvm node invisible to services/autostart; launchd PATH hides Homebrew deno from the tray's web-UI jobs (same as ffmpeg today); red icon in Settings for the optional row.
Could not check: the Docker transcript was 0 bytes at review time (run restarted after the server restart).
