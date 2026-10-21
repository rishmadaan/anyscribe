# Lead fix, round 4: audit/building-docs commit 6d6c45cf7a03c274523a5bc770aa619cd8d46f28 (parent 5ed32bd)

Four one-line wording edits applied by the lead, exactly as the round-3 reviewers proposed:
1. COMMIT_CHECKLIST.md:74 (Astra B1): check-docs rejects versions that differ from pyproject.toml, except version-pin-ok lines; no longer claims "no hardcoded versions".
2. providers.md:54 (Opus B1): ElevenLabs cell "~30-word timestamped segments".
3. release-checklist.md:165 (Opus B2): row now builds the wheel first (rm -rf dist && python -m build && pip install dist/*.whl).
4. release-checklist.md:121 (Opus B3): create the GitHub Release only when the workflow failed after the PyPI upload or after a manual twine publish.
Checks: check-docs exit 0; git diff --check clean.
