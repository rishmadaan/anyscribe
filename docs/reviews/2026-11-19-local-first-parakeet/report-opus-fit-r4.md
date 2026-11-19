Copied from the review run folder; absolute home-folder paths rewritten as ~ paths; the byte-exact original stays in ~/.review-runs/2026-11-19-local-first-parakeet/.

~~~~~
FIT REVIEW, round 4 (final). Target: feat/local-first-parakeet @ 90bc0cf. Read-only: I wrote no files and ran no tests, builds or servers.

## 1. Verdict

**CONDITIONAL on R4F1.** R4F1 is a one-line copy change in the Settings setup window, small enough for the lead to make without another fix round.

- **R3F1: FIXED.** The hint now names a step that really switches transcription to this computer, prints once per run, and shows on its own lines on the web.
- **R3F2: FIXED.**
- **R3F3: FIXED.**
- **New problem:** the fix for R3F1 added a contradictory sentence to the Settings setup window. That is R4F1.

## 2. Status of the round-3 fit findings

| Id | Status | Evidence |
|---|---|---|
| R3F1 hint loops and renders as one run-on line | FIXED | **Code:** `providers/base.py:12-15` now says "run `anyscribe onboard` and choose On this computer (in the dashboard: Settings, then Run setup wizard)". The pre-flight error carries the hint (`core/preflight.py:64`). The CLI drops the duplicate copy (`cli/transcribe.py:124-127`, `cli/batch.py:208-212`).<br>**Screens:** `r4-f1-transcribe-error-1440.png` shows the key error, Fix, Or and the hint, each on its own line. `r4-f1-settings-nextrun-1440.png` shows the WARNING and the hint as two lines.<br>**Proof:** the proof's real CLI walk on a fresh home goes onboard, then `→ local (config)`, then the transcript is saved. The hint is not a loop any more. |
| R3F2 tip gives a CLI command on the web and stays while pending | FIXED | **Code:** `local_recommend.py:300-304` adds the web wording. `web/routes/local.py:99-100` drops the tip while a default is pending (downloading or failed).<br>**Screens:** `r4-f23-suggest-hindi-1440.png` shows "Try it: click the Parakeet v3 card below." `r4-f23-pending-1440.png` has no tip while "Downloading; becomes your default when done" is showing. The CLI and MCP keep the command (`check_status()` defaults to `web=False`; `mcp/server.py:589`). |
| R3F3 Use offered for the current default | FIXED | **Code:** `LocalModelPicker.tsx:447-452`.<br>**Screen:** `r4-f23-suggest-hindi-1440.png` shows "Already downloaded." and a green "This is already your default", with no Use button.<br>**Proof:** the mutant walk shows the extras' readiness is checked. A mix without Turbo downloaded still gets the 1.6 GB Use button. |

## 3. New findings, most severe first

**R4F1. should-fix. CONFIRMED (code + screenshot).** After setup, the Settings setup window says the new model is the default, then says it is not used yet.

- **Where:** `ui/src/components/LocalSetupModal.tsx:144-152`, the text set at `core/local_setup.py:62-65` (`USE_LOCAL_TIP`), and screenshot `r4-f1-modal-result-1440.png`.
- **What the window shows:**
  - "✓ Parakeet v3 is ready and is your default."
  - "To use it for every transcript: `anyscribe config set quality free` (or pick 'free' under What runs by default)."
- **Scenario:**
  1. A key-free person is on Settings. The loudest button on the page is the orange "Set up local transcription" on the local card, not the hint's "Run setup wizard".
  2. They click it, wait for the download, and read "is ready and is your default" with a green tick.
  3. They click Done and go to Transcribe. The proof records the saved settings as `provider openai, quality balanced`, so the run fails with the same missing-key error.
- **Why the second line doesn't help:** it reads as an optional extra, not as "you are not done". On a web screen it also leads with a terminal command, and the backticks show as literal characters.
- **Who it hits:** the reader this PR is for, and exactly the case the hint was added to cover.
- **Fix (copy only):**
  1. When `use_local_tip` is set, change the first line to "… is ready and is your default local model."
  2. On the web, make the tip "anyscribe still uses openai for new transcripts. To use this computer instead, pick 'free' under What runs by default." Drop the CLI command there; keep it for the CLI output, the same split as R3F2.
- **Optional, simpler for him:** a "Use it for every transcript" button that saves quality free. This is a scope call for the lead, not required.

**R4F2. nit. CONFIRMED (code + proof).** The hint says `anyscribe onboard`, but onboard refuses on any home that already has a config file.

- **Where:** `providers/base.py:13` and `cli/onboard.py:92-103, 555-559`. The pre-flight error stacks "Or: anyscribe onboard --force" directly above the hint's "run `anyscribe onboard`" (`r4-f1-transcribe-error-1440.png`).
- **Scenario:**
  1. A person has already run `anyscribe local setup`, or saved anything in Settings, so the config file exists.
  2. They follow the hint.
  3. Onboard prints "Already configured … Pass --force to re-run". The proof's own walk hit exactly this.
- **Why it's only a nit:** onboard's message names the fix, so this costs one extra step, not a loop. But two near-identical commands on adjacent lines read as a puzzle.
- **Fix:** make the hint say `anyscribe onboard --force`, or drop the "Or: anyscribe onboard --force" line from the pre-flight error when the hint follows it.

**R4F3. nit. PLAUSIBLE (screenshot only). Not introduced by the round-3 fixes; same kind of problem as R3F3.**

- **Where:** `LocalModelPicker.tsx:452` (the Use button condition) and screenshot `r4-f23-pending-1440.png`.
- **Problem:** while Parakeet v3 is already "Downloading; becomes your default when done", the earlier English suggestion still offers "Use Parakeet v3 (downloads 670 MB)". Clicking it most likely repeats an action already under way.
- **What would settle it:** click Use in that state and check the download queue gets no second entry.
- **Fix:** treat "primary equals the pending default" the same way as "already your default", and show "Downloading; becomes your default when done" instead of the button.
- **Can wait:** yes, this can wait for a later change.

## 4. Answers to the brief (advice, not findings)

- **Is this the job he asked for, and the simplest instrument?**
  - Yes. Round 4 did not widen scope: copy, two CSS classes, one server-computed tip and one condition.
  - Computing `use_local_tip` on the server (`local_setup.py:352-363`) means the CLI and the web give the same answer.
- **Does it read right to its reader?**
  - Yes on the Transcribe error box, the Next run box, the Parakeet tip and "This is already your default".
  - The exception is R4F1: the setup window is the one screen where a non-developer will believe they are finished when they are not.
- **The WARNING (lead evidence 2):**
  - A key-free person who skips setup still sees it. It now carries a working way out on its own line.
  - It is unreachable after either wizard. After the Settings setup window it remains, which is R4F1.
- **Card numbers (lead evidence 3):** unchanged since round 3, and honestly captioned. The screenshot footer reads "measured on English audio on a 6-core desktop processor without a graphics card. Your computer may be faster or slower."

## 5. Pending owner checks

- **Mac re-measure with the CPU provider forced:** still not recorded in the proof.
- **mockup.html in the public repo:** it says "your desktop (i5-10600K)" and "transcripts already in your vault". Keep it or mask it? Carried over from rounds 2 and 3.
- **R4F1's direction (copy or button):** whether he wants the setup window to offer a one-click "Use it for every transcript" or just say plainly that the default is still the cloud.

## 6. What I could not check, and what I inspected

**Could not check:**
- No browser or CLI walk.
- To settle R4F3, on a local Turbo user's Settings: answer English, click the Parakeet v3 card, then click "Use Parakeet v3 (downloads 670 MB)", then run `curl -s localhost:<port>/api/local/status | python -c "import sys,json;d=json.load(sys.stdin);print(d['pending_default'],[m['size'] for m in d['models'] if m.get('queue_position',-1)>=0])"`. The field names come from `web/routes/local.py:96-110` and the queue field name is my guess.
- To see R4F2: on a throwaway home with no keys, run `anyscribe local setup --model tiny --yes && anyscribe onboard` (the proof already shows the refusal).

**Inspected:**
- **Packet:** brief-r4-fit.md, ask.md, lens.md, declined.md, review-log.md, fix-plan-r3.md, the round-3 fit report in findings.md, and proof.md's "Round 3 fixes".
- **Diff:** `git diff 5551230..90bc0cf` for cli/, core/local_setup.py, core/preflight.py, core/local_recommend.py, providers/base.py, web/routes/local.py and ui/src. Also the `local_hint()` call sites, onboard's refusal on an existing config, the Settings tier rows (selectable, `SettingsPage.tsx:398-412`) and the MCP status block.
- **Screenshots:** `r4-f1-transcribe-error-1440`, `r4-f1-settings-nextrun-1440`, `r4-f1-modal-result-1440`, `r4-f23-suggest-hindi-1440`, `r4-f23-pending-1440`.
- **Not opened:** the other r4-*.png (the old-code and mutant variants); I relied on the proof's description of those.
~~~~~
