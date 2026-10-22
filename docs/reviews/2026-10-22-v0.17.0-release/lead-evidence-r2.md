# Lead evidence, round 2 (branch at 6ee52d746faabf63e03cb7764b06bab475e162de)

- CI on c791f91 (round-1 target): all green (python 3.11, 3.12, 3.14; frontend; docs). CI on 6ee52d746faabf63e03cb7764b06bab475e162de is in flight.
- pytest 486 passed, 1 skipped; ruff check src tests scripts clean (target-version py311); check-docs.py exit 0; build-docs.py output committed; bash -n install.sh ok. No pwsh on this Mac, so install.ps1 was not parsed by PowerShell.
- Full extras dry run, `pip install --dry-run --ignore-installed ".[dev,mcp,local,tray]"` in clean venvs: Python 3.11.15, 3.12.14, 3.13.0, 3.14.7 each resolve to fastapi 0.159.1, starlette 1.9.0, mcp 2.3.0, faster-whisper 1.2.1 (ctranslate2 4.8.3), pystray 0.19.5, pyobjc-framework-Cocoa 12.2.2.
- Lowest-floor proof on 3.11: `pip install --dry-run --ignore-installed ".[dev,mcp]" "fastapi==0.133.0" "starlette==1.3.1"` resolves ("Would install"); `"." "fastapi==0.132.0"` fails with "Cannot install anyscribe==0.16.5 and fastapi==0.132.0 because these package versions have conflicting dependencies".
- PyPI JSON 2026-10-22: fastapi 0.131.0 and 0.132.0 pin starlette<1.0.0,>=0.40.0; 0.133.0 pins starlette>=0.40.0 (open-ended); 0.134.0+ pin starlette>=0.46.0. starlette 1.3.1 requires_python >=3.10.
- OSV API 2026-10-22: starlette 1.3.0 -> GHSA-82w8-qh3p-5jfq, PYSEC-2026-249; starlette 1.3.1 -> none.
- mcp 2.3.0 requires starlette>=0.27 (python<3.14) / starlette>=0.48.0 (python>=3.14), open-ended.
- `anyscribe install-skill --force` exists (src/anyscribe/cli/skill_cmd.py:51).
- Not run: install.sh or install.ps1 on a real Ubuntu 22.04 or Windows machine; a real Python 3.10 (none on this Mac).
