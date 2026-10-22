# Lead evidence, round 1 (commands run by the lead on the branch at c791f91, Mac, Python 3.13 venv unless stated)

- `python -m pytest -q`: 486 passed, 1 skipped.
- `ruff check src tests scripts`: All checks passed.
- `python scripts/check-docs.py`: exit 0.
- `python scripts/build-docs.py`: regenerated landing/docs/getting-started.html (3 lines), committed.
- `bash -n install.sh`: ok.
- Python 3.11.15 venv, `pip install --dry-run .`: resolves; would install starlette-1.9.0, fastapi-0.159.1, python-multipart-0.0.32, beaupy-3.12.0, uvicorn-0.54.0.
- Python 3.11.15 venv, `pip install --dry-run . "starlette==1.0.0"`: "ERROR: Cannot install anyscribe==0.16.5 and starlette==1.0.0 because these package versions have conflicting dependencies." (the floor bites).
- PyPI JSON checked 2026-10-22: starlette 1.3.1 requires_python >=3.10 (2026-06-12); fastapi 0.130.0 pins starlette<1.0.0,>=0.40.0; fastapi 0.136.0 (2026-04-16) pins starlette>=0.46.0 open-ended; fastapi latest 0.159.1 pins starlette>=0.46.0.
- Not run: GitHub Actions on this SHA (in flight), install.sh or install.ps1 end to end, a real 3.10 interpreter (none on this Mac).
