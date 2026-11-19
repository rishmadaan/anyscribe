# Fix plan, round 3 (lead's choices; binding where it decides)

Round 4 was approved by the owner over the cap, Claude-only. Fix R3C1, R3C2,
R3C3, R3F1, R3F2, R3F3. Each fix gets a test that fails on 5551230 and passes
after, asserting identities (which provider, quality and model survived;
which default is saved; the response body), never counts.

1. **R3C1 lost config updates.** One process-wide lock for every
   read-modify-write of config.yaml: add it next to `load_config`/`save_config`
   in `config/settings.py` (a `threading.RLock` and a small
   `update_config(mutator)` helper that loads, mutates and saves under the
   lock). Route every writer through it: `core/config_set.set_value`, the web
   `PUT /api/config` multi-field update and its rollback, `run_setup`'s
   default switch, the download worker's activation, headless and interactive
   onboarding saves, and any other `save_config` caller found by grep (list
   them in proof.md). Cross-process writers (CLI while the server runs) are
   out of scope; say so in a code comment
   (`# shortcut: in-process lock only; a CLI write while the server runs can
   still race, upgrade to a file lock if that is ever reported`). Test: a
   deterministic interleaving (background set_value of local_model vs a
   foreground provider/quality save) leaves provider, quality AND model all
   at their latest values.

2. **R3C2 choose response.** `choose()` builds its response from a snapshot
   captured under the queue lock before the worker can run (request-owned
   values), never from shared pending state read afterwards. Tests: worker
   completes before the response is built; a second choose completes during
   the first. Both return 200 with a correct body and the right saved default.

3. **R3C3 one owner of activation.** A monotonic choice generation in the web
   download-queue state: every accepted `choose` and every web setup start
   takes the next number; an activation (the worker's switch or the end of a
   web setup) switches the default only if its number is still the latest,
   otherwise it records "superseded" and leaves the default alone. Web setup
   passes this check into `run_setup` (a predicate/callback argument; the CLI
   keeps calling `run_setup` without it, unchanged behaviour). Test: start
   setup of parakeet-v3, choose a runnable `small` meanwhile, finish the
   setup: saved default is exactly `small`, setup status says superseded.

4. **R3F1 hint.** Text everywhere it is appended: "Or transcribe free on this
   computer, no key needed: run `anyscribe onboard` and choose On this
   computer (in the dashboard: Settings, then Run setup wizard)." Print it at
   most once per run (it is currently printed twice: warning and error).
   Web: the two `<p>` elements that show notes/errors get
   `whitespace-pre-line`. When the provider is not local, `anyscribe local
   setup` (CLI) and the web setup result end with: "To use it for every
   transcript: `anyscribe config set quality free` (or pick 'free' under What
   runs by default)." Test: after following the step the hint names in a
   headless test (onboard --yes --provider local ...), the next plan's provider is local.

5. **R3F2 tip.** Hide the Parakeet tip in Settings while a pending default
   exists or right after a failed switch; on the web it ends "Try it: click
   the Parakeet v3 card below." CLI and MCP keep the command.

6. **R3F3 current default.** When the suggestion's primary is the current
   default and every extra is runnable, show "This is already your default"
   instead of the Use button.

Do not touch anything else. Full suite, ruff, UI tsc/lint/build with
web/static rebuilt, docs check. A browser walk of R3F1 (Transcribe error box
and Settings Next run box on a key-free un-onboarded home), R3F2 and R3F3,
screenshots to ~/.review-runs/2026-11-19-local-first-parakeet/screens/ with
an r4- prefix.
