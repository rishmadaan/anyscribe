(Opus 5.5, effort high, fit reviewer, round 3, target af41426. Verdict: CONDITIONAL on I1, I2, the pinned Docker run landing green, CI green.)

Round-2 ledger: all FIXED (Sol I1-I5, I7; Opus I1-I5); Sol I6 FIXED in method, pending the pinned transcript. No new code defects; I3 is a docs overclaim from the round-2 wording, I6 a test gap on a must-never.

I1 should-fix CONFIRMED CHANGELOG 0.17.1: never tells an upgrading user (pip / anyscribe update) that a runtime is now wanted or how to get it. Add the bullet given.
I2 should-fix CONFIRMED docs/reviews/2026-10-22-youtube-js-runtime/: about 20 absolute ~/.review-runs paths in briefs, reports and lead evidence about to enter a public repo; scrub to repo-relative / <review-run>/ before committing, grep for the home-folder prefix after.
I3 nit CONFIRMED commands.md:310,1182: "Startup messages ... go to stderr" overclaims; the Windows one-time PATH notice (cli/main.py:117-146) still prints to stdout. Add the exception.
I4 nit CONFIRMED README.md:33 still says pip users install yt-dlp themselves; getting-started Windows appendix still has a bare `python -m pip install yt-dlp`.
I5 nit CONFIRMED skill troubleshooting and SKILL.md:30: the Linux fix uses sudo and a remote script that Claude's shell cannot run; tell the user and hand them the commands; SKILL.md's installer description should mention ffmpeg and the runtime.
I6 nit CONFIRMED no test of cli/download.py::_download_video; Instagram byte-identity and the YouTube flag are guarded by reading only.
I7 nit CONFIRMED CHANGELOG/journal "when no Python is present" is narrower than the code (runs whenever no 3.11+ is found).
I8 nit CONFIRMED BACKLOG 0.17.0 row lost "(current)" before 0.17.1 is published.
I9 nit PLAUSIBLE: ps1 never reads StandardError (a flood blocks, bounded by the 10 s kill); node pre-release banners rejected; deps.py install_pip still bare "pip install yt-dlp".
I10 nit CONFIRMED install.sh: the Linux "Install Deno?" prompt does not say the script edits the shell profile.
Answers: regexes handle CRLF, rc suffix on deno, node on stderr (python yes, installer no); probe_version under set -e fine; BASH_REMATCH fine; empty loop element skipped; Instagram argv byte-identical; check_python test passes for the right reason but cannot catch a lost resolve_python guard; pseudo-terminal tests ~30 s; CHANGELOG true sentence by sentence except I1 and I7; no version literals.
Pending owner: bare red icon in Settings for the optional row; launchd/nvm PATH for tray jobs (same as ffmpeg); runtime size ~100 MB.
Could not check: pinned Docker transcript (0 bytes at review time); CI; Windows; Deno's script without --yes in a no-terminal shell; whether --js-runtimes adds to or replaces the default deno; pip resolution 3.11 to 3.14.
