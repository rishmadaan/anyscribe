(Opus 5.5, effort high, fit reviewer, round 1, target c791f91. Verdict: CONDITIONAL on CI passing on c791f91 and I1 to I4 fixed or knowingly accepted before the tag.)

I1 should-fix CONFIRMED install.sh:228: Ubuntu 22.04 (python3 = 3.10) loops: apt install python3 installs nothing, die says "Python installed but no python3.11+ found", re-run repeats. Fix: honest die text naming python3.11 packages / python.org; try python3.11 as the apt package.
I2 should-fix PLAUSIBLE install.sh:287: pipx install uses pipx's own interpreter (3.10 on Ubuntu 22.04), which resolves anyscribe to 0.16.5 and prints success. Fix: pipx install --python "$PY".
I3 should-fix PLAUSIBLE install.ps1:80: after winget install, no version re-check; an all-users 3.10 earlier on PATH wins and 0.16.5 installs as "success". Fix: re-run the version test after Refresh-Path; try py -3.12.
I4 should-fix CONFIRMED docs/user/getting-started.md:297-300: the Linux fix `sudo apt install python3 ...` leaves 3.10 on Ubuntu 22.04. Add the python3.11 alongside instruction.
I5 should-fix CONFIRMED CHANGELOG Breaking bullet: say nothing breaks on 3.10, update/pip report up to date at 0.16.5, how to move (install 3.11+, reinstall with it, installer does it), settings and transcripts stay.
I6 nit CONFIRMED CHANGELOG wording: "1.3.1 floor" jargon; "CI now also tests 3.14" -> "Python 3.14 is now supported and tested"; "hints no longer name the old command" wrong; `anyscribe --clipboard` reads as a feature; "about 40" undercounts what merged (drop the numbers).
I7 nit CONFIRMED journal tldr "two of the four owner decisions" mismatches; three of four questions settled.
I8 nit CONFIRMED pyproject.toml:106 ruff target-version = "py310" still names the dropped floor.
I9 nit CONFIRMED install.sh:54 candidate list lacks python3.14.
I10 nit PLAUSIBLE pyproject comment overstates: pip would backtrack anyway; 0.131-0.135 pins unverified.
Answers: right job and instrument; ps1 and deps.py checks correct; min_version unused (cosmetic); rehearse-migration needs python3>=3.11 locally (acceptable); skill auto-refresh claim matches cli/main.py:56-113; release.sh needs a clean tree (the untracked review record folder must be committed first) and main checked out; BACKLOG "[ ] Open from the audit" under a released version could read as unfinished (label "Carried forward").
Could not check: CI, fastapi 0.131-0.135 pins, OSV for starlette 1.3.0/1.3.1, mcp's starlette pin, real Ubuntu 22.04 / Windows runs (commands given).
