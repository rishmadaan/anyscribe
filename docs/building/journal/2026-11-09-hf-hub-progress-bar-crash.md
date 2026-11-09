---
type: troubleshooting
tags: [local, faster-whisper, huggingface, web-ui, models]
tldr: "Dashboard model downloads crashed on huggingface_hub >= 1.x: its bars are disabled with no TTY, and a disabled tqdm has no .unit. Fixed in 0.18.1."
---

# Model download crash: `'_ProgressTqdm' object has no attribute 'unit'`

**Symptom.** A new user installing from the dashboard saw the error above on
every model download attempt; the install log looped "faster-whisper
installed / downloading model / error".

**Cause.** `faster-whisper` only pins `huggingface_hub>=0.21`, so new installs
get 2.x. Since 1.x, `snapshot_download` hands `tqdm_class` two whole-snapshot
byte bars (transfer and reconstruction, each with the full total) and, for an
HF tqdm subclass, passes `disable=None`, which tqdm turns into `disable=True`
when there is no TTY (the Web UI's worker thread). A disabled tqdm returns
from `__init__` before setting `.unit` and never counts `.n`. On 0.x the
class only ever saw the files-count bar, so the bug could not show; the old
unit test used a fake base that always set `.unit`.

**Fix.** `_ProgressTqdm.__init__` pops `name`, forces `disable=False`, writes
to a null file and calls plain `tqdm.__init__`, skipping the HF base init (so
`HF_HUB_DISABLE_PROGRESS_BARS` can't re-disable it either; nothing is drawn
anyway). Progress reports the furthest byte bar, not the sum, which had shown
about twice the model size. Basing on plain `tqdm` instead was tried and
breaks on 1.x, which passes `name=` to any class.

**Verified.** Real `Systran/faster-whisper-tiny` downloads with stdin
detached on huggingface_hub 0.36.0 (no byte bars, spinner), 1.2.0 and 2.4.0,
each with `HF_HUB_DISABLE_PROGRESS_BARS` 0 and 1: no crash, final report
(78207087, 78207087). The new test fails on the old code with the user's
exact error.
