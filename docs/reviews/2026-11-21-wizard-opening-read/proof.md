# Proof: the setup wizard's opening read reaches the local step in order (review L1), round 0

Implementer: Claude Opus 5.5 (Agent tool). Worktree `~/labs/projects/anyscribe-wt/wizard-l1`, branch `fix/wizard-opening-read`, base `41ee458` (checked with `git rev-parse --short HEAD` before editing).

Commits:
- `f03d02d` Setup wizard: the opening status read respects where the wizard is (review L1)
- `5cb3235` Rebuild the dashboard bundle for the opening-read fix (`index-Bl10hv_a.js`)
- `37a2f58` Records for the opening-read fix: backlog tick, journal follow-up 2
- `9640add`, `73dec34` this file
- After the lead's answers (same round 0; section "Lead's round 0 change" below):
  - `6f411a6` drop the equivalent "no start sent" half of the hand-off check; spec.md records the lead decision
  - `a809629` rebuilt bundle (`index-BgvSyGg6.js`). **This commit fails `npm run lint`**: see below
  - `1def075` take a handed reply while rendering, not in an effect (lint clean again)
  - `c1d9be0` rebuilt bundle (`index-CJbYAiX1.js`), the one every result below was checked on unless it says otherwise
  - the records commit after it (journal, this file)

Raw evidence lives outside the repo in `~/.review-runs/2026-11-21-wizard-opening-read/` and is not committed:
- `instruments/`: yesterday's harness (`harness.js`, `cases.js`, `lead-r2.js`, `serve.py`, `slowproxy.py`) with the results port moved to 8477; new `l1-cases.js` (L1A to L1D), `mutate.py` (five new mutants), `buildmut.sh` (builds one mutant into a separate copy of the package), `show.sh` (prints a result file).
- `instruments/results/*.json`: every run of today, saved by the page itself. Yesterday's results that came along with the copy are in `results/from-lock/`.
- `screens/real-reload-watched-1280.png`, `screens/real-reload-escape-asks-1280.png`: the real run, each opened and checked.
- `old-src/`: the package at `41ee458` (bundle `index-DEtcgFqh.js`, the same as `5fb5d1e`; the packet commit changed only `docs/reviews`).

## What changed (`ui/src/components/OnboardingWizard.tsx`)

- **Where the wizard is, known when the reply lands (rule 1).** `setStep` is now a small wrapper that, together with the step, keeps a ref: `never` → `showing` when the local step is first asked for → `left` when the wizard moves anywhere else. `left` stays `left` for the rest of this wizard. All existing `setStep` call sites are unchanged. The opening read's handler reads the ref when the reply arrives, not a value captured when it was sent:
  - running and `left`: dropped;
  - running and `showing`: `setAdopt(reply)` only; the form and the route are untouched;
  - running and `never`: as before (form set to local, on, the running model; reply handed over; route to `offline_opt_in`).
- **The step decides (rule 2).** `adopt` is now the reply itself (`LocalStatusResponse | null`), not a boolean. At mount, `useState(adopt !== null)` as before, so watching is true on the first render. While rendering, the step takes a handed reply it has not taken yet only if `status === null` (no accepted read of its own; a start needs one too, so that is enough: lead decision). Taking it sets `taken` and `setWatching(true)`; an effect on `taken` then does the rest of what the step's own running read does: `onSetEnabled(true)`, `onSelectSize(setup_last_model)` when set. Otherwise nothing happens, and the form is never written for an ignored reply. (Round 0 first had this in one effect with a second condition, `startGenRef.current === 0`; see "Lead's round 0 change".)
- **Kept (rules 3 and 4).** `onRunning` still has one call site (`git grep -n "onRunning(" -- ':!docs/reviews'` gives `OnboardingWizard.tsx:775` only); `watched` and `confirmClose` are still set only through it and the existing buttons. `goWorkspace` and the step's Back still clear the handed reply (now `setAdopt(null)`). Nothing else in `ui/src` or `src/anyscribe` changed except the rebuilt bundle.

## Proof bar

### Sol's two variants and variant C: fail on the old build, pass on the new

Old build: `old-src` served on 8472 (`index-DEtcgFqh.js`, `results/old-l1.json`). New build: the worktree on 8471 (`index-Bl10hv_a.js`, `results/new-l1.json` and `results/final-all.json`). Same harness, same tab, a fresh empty HOME per server, `--local-only`.

**L1A (Sol's variant A).** The opening read says Whisper Small is running and answers 4 s late. The person reaches Local transcription first. Every one of the step's own reads fails. Requests on the new build: opening `over+4000 → 200 (4514 ms)`, step reads `fail → TypeError` at 198, 1698, 3198 ms, then the loop restarts at 4514 ms when watching starts.

| Check | Old build | New build |
|---|---|---|
| On the local step before the reply, not watched, reply pending | pass | pass |
| The reply landed (200, running) after at least two failed step reads | pass | pass |
| After the reply: S13 line, Skip shown, Back disabled, "Setting up… [disabled]" | **FAIL**: no S13, Back `enabled`, button "Install now", S12 shown | pass |
| Escape: "Close setup?" opens, focus on Keep setting up | **FAIL**: `{"dialogOpen":false,"flag":null}`, the wizard closed at once | pass |
| A backdrop click asks first | not reached (closed) | pass |
| Skip for now asks first; `scribe_onboarding_dismissed` is `null` | not reached | pass |
| A click on Back does nothing: still Local transcription, watched | not reached | pass |
| Reads come back (running, naming no model): selected card `small`, "Downloading Whisper Small… 30%" | not reached | pass |
| Close setup closes, flag `null` | not reached | pass |

**L1B (Sol's variant B).** The opening read says Whisper Small is running and answers 8 s late. Meanwhile the person picks Whisper Base, starts it (200), the next read says stopped and runnable, and the wizard goes on to Workspace (by about 0.8 s). Then the reply lands (8215 ms).

| Check | Old build | New build |
|---|---|---|
| On Workspace before the reply; reply pending | pass | pass |
| The reply landed: 200, running Whisper Small | pass | pass |
| 2 s later: still "Workspace location", no S13 line, Skip shown, no "Close setup?" | **FAIL**: title "Local transcription", picked `small`, S14 "Setup didn't finish…" (the step's own read said not running) | pass |
| Back from Workspace: Local transcription, not watched, Back enabled, picked `base` | **FAIL** (routed elsewhere already) | pass |
| Escape closes at once, flag `null` | pass | pass |

**L1C (variant C).** The opening read says Whisper Small is running and answers 4 s late. The step's own read (not running) was accepted first and Whisper Base was picked.

| Check | Old build | New build |
|---|---|---|
| The step's own read answered 200 before the reply; reply pending | pass | pass |
| The reply landed: 200, running Whisper Small | pass | pass |
| Ignored: not watched (no S13, Back enabled, no "Setting up"), picked `base` | **FAIL**: picked `small`, button "Download Whisper Small (460 MB)": the old shell overwrote the pick, though it did not start watching | pass |
| Escape closes at once, flag `null` | pass | pass |

C was expected to pass on the old build, since the old step ignored a late reply; it fails because the old shell wrote the form (the pick) for a reply the step did not take. That is the "form must not be written for a reply the step then ignores" rule, seen.

**L1D (extra, for mutant ii).** The step's read loads the cards, Whisper Base is picked, the start is refused (500) while further reads fail, then the 5 s-late reply (running Whisper Small) lands. New build: ignored; not watched, Back enabled, picked `base`, "Try again" kept; Escape closes at once, flag `null`. Not run on the old build.

### Regressions: 31 of 31 pass on the committed bundle (`results/r0b-final-all.json` on `index-CJbYAiX1.js`; earlier `results/final-all.json` on `index-Bl10hv_a.js`)

T1, T1_500, T2, T3, T4, T4_notRunning, T4_refused, T5, T5_late, T6, T7, T8, T9, T10, T11, T12, T12b, F4, F1, T13, TG, T4v2, R3C1, R3C2, L3, LF3 (yesterday's 26), LR2 (the lead's post-cap checks from `lead-r2.js`, run as one case), and L1A, L1B, L1C, L1D. The S11 cases are T1, T7, T13, TG, LF3, R3C1; the S13 checks are in every `watched` assertion.

No existing case was changed. One earlier full run (`results/new-all.json`) had T1_500 and T2 fail while I was building mutants in parallel: in both, a real status read was still `pending` 1.6 s after it was sent, so the progress line had not updated at the check. Run again alone (`results/new-rerun.json`: T1_500, T2, T1 pass) and in the final run with nothing alongside, they pass. I read that as load on the real server, not the change; T1_500 and T2 do not touch the opening read.

### Mutation: each new guard removed in turn (first pass on `index-Bl10hv_a.js`; the final pass is in "Lead's round 0 change") (`instruments/mutate.py`, built by `buildmut.sh` into a separate package copy on 8473; the worktree source was restored with `git checkout` after each build)

| Mutant | Change | Killed by | What the failing case saw |
|---|---|---|---|
| **Mi** (i) | "left the local step: drop" removed: `if (!s.setup_running) return;` | **L1B** (`results/Mi.json`) | 2 s after the reply: title "Local transcription", picked `small`, S14, instead of Workspace. L1A, L1C, T5_late pass. |
| **Mii** (ii) | the step's "nothing newer" check removed: `if (!adopt) return;` | **L1C**, **T5_late** (`results/Mii.json`) | L1C: S13 line, Back `disabled`, "Setting up… [disabled]", picked `small`; Escape left the wizard open (asked) instead of closing. T5_late: watched with S14, and status reads never stop (the not-running read ends watching, `status` changes, the effect accepts the old reply again). L1A, L1B pass. |
| **Mii_status** (ii, first half) | only `status !== null` removed | **L1C**, **T5_late** (`results/Mii_status.json`) | Same as Mii. |
| **Mii_start** (ii, second half) | only `startGenRef.current !== 0` removed | **survives**: L1A, L1B, L1C, L1D, T5_late, R3C2 pass (`results/Mii_start.json`) | An equivalent mutant (below). **The half was removed from the code by the lead's decision**, so this mutant no longer exists. |
| **Miii** (iii) | the hand-off to a mounted step removed: `if (showing) return;` | **L1A** (`results/Miii.json`) | After the reply: no S13, Back `enabled`, "Install now [disabled]"; Escape closed the wizard at once. L1B, L1C, L1D, T5_late pass. |

**Mii_start is equivalent, not a weak test.** In the one mount that can receive a hand-off after mount (the first visit, while the ref says `showing`; a second visit is `left`), a start needs `selected`, and `selected` only gets a value from the step's own accepted read (the recommendation or a card click, both after `status` is set) or from the never-shown branch (which mounts the step already watching, so the start button is disabled until an accepted read ends watching, which sets `status`). So whenever `startGenRef.current !== 0`, `status !== null` already holds and the first half returns. L1D is the nearest reachable ordering (a refused start with failing reads), and it passes under the mutant for that reason. The lead removed the half (house rule: a guard no test can tell apart is removed); spec.md rule 2 now records that.

### Checks

```
$ uvx "ruff>=0.4,<0.16" check src tests scripts     # ruff 0.15.22; the main venv has no ruff
All checks passed!
$ cd ui && npm run lint && npm run build
> eslint .            (no findings)
../src/anyscribe/web/static/assets/index-Bl10hv_a.js   433.08 kB   (same as committed)
$ git diff --exit-code -- src/anyscribe/web/static    # CI's bundle check
(clean)
$ python3 scripts/build-docs.py && git diff --exit-code landing/docs && python3 scripts/check-docs.py
rendered 6 pages + index → landing/docs   (no diff; check-docs exit 0)
$ HOME=<throwaway> PYTHONPATH=<worktree>/src uv run --no-project --python ~/labs/projects/anyscribe/.venv/bin/python \
    --with "pytest>=8.0" --with "huggingface-hub>=0.21" python -m pytest -q
1006 passed, 9 skipped, 192 warnings in 63.44s
```

The main checkout's venv has neither pytest nor ruff, so both ran from uv's temporary overlay environments (nothing installed into that venv). A first pytest run without the dev extra's `huggingface-hub` gave 8 errors, all `ModuleNotFoundError` in `tests/test_local_ready.py`; with it, all pass. No Python changed.

### The real run (no harness, no fakes)

- Server: the worktree's code with the committed bundle, `HOME=<new empty folder>`, port 8474, `--local-only`, `HTTPS_PROXY` through `slowproxy.py` (200 kB/s per connection). It ran inside a uv overlay environment on top of the main venv with `faster-whisper`, `av<19` and `onnx-asr` added, so the setup skipped its engine install and nothing was written into the main venv (afterwards `import faster_whisper` in the main venv still fails, as before).
- Real clicks in my own preview tab: Let's go, On this computer, More models, Whisper Tiny, "Download Whisper Tiny (75 MB)". The server then said `setup_running: true, setup_last_model: tiny`, 6.7%.
- **Reload mid-setup:** the page reloaded; the wizard opened on Local transcription with "Back is off until setup finishes. Skip for now asks first.", "Downloading Whisper Tiny… 12.7%", "Setting up…", Back disabled, the Whisper Tiny card selected (`screens/real-reload-watched-1280.png`).
- **Escape asks first:** a real Escape key press, after a click on the dialog title to give the page focus: "Close setup? The download keeps going…" with focus on Keep setting up, flag `null` (`screens/real-reload-escape-asks-1280.png`). A real Enter hid it; the download continued (26.6%).
  - My first Escape press, sent straight after the reload with the page unfocused, changed nothing: no box, the dialog still open, flag `null`. Had it reached the page's handler while not watched, the wizard would have closed, so I read it as not delivered. It is not counted as evidence either way.
- The download finished (`setup_outcome: set_up`, `tiny` runnable) and the page moved on to Workspace by itself.
- Disk: `df -h ~` 30 GB free before and after; the throwaway home (75 MB model, 462 MB uv cache) is deleted.

## Records

- `BACKLOG.md`: the "Before the next PyPI release" L1 line is ticked, with "Done in the L1 follow-up (branch `fix/wizard-opening-read`)". There is no PR yet, so the branch stands in for the PR's short form; the lead adds the number when it is opened.
- `docs/building/journal/2026-11-20-onboarding-wave1.md`: a "Follow-up 2 (2026-11-21)" section: what L1 was, the rule and why, the proof.
- `CHANGELOG.md`: unchanged. The W6 entry's "Reloading the page picks the running download back up" holds (seen in the real run), and no line describes the opening read's ordering.

## Where I think the spec is wrong, and choices to review

1. **Half of rule 2's check cannot fire.** "No start request sent in this mount" is implied by "no accepted status read" in every reachable state (traced under Mii_start). **Resolved: the lead removed it** (spec.md, rule 2's added line).
2. **A second visit to the local step.** Rule 1 names never shown, showing and left, but not "left, then shown again". I made `left` final: a reply landing on a second visit is dropped, because the first visit's reads and any start are newer than it. Reading "showing now" literally would hand it to the new mount, which has not read yet, and a stale "running" could then start watching and end in a false "Setup didn't finish". **Accepted by the lead as built, with this residue: if every read on the first visit failed, the old reply no longer helps a second visit.** The step's own reads still show the running download once they get through. **Superseded in round 1 (C1/F1):** the lead closed this residue in code with the "heard" rule; see "Round 1 fixes".
3. **Variant C failed on the old build too**, by overwriting the pick, not by watching. The spec framed C as a guard check; it is also a defect the old code had.
4. **"Has been shown" is set when the step is asked for**, in the `setStep` wrapper, not after React renders it. An effect would leave a gap between a `setStep` from a status callback and the commit in which a reply could still be routed by the old value.

## What I could not prove

- The real run used the Linux preview browser only; no Mac or Windows, no screen reader.
- React StrictMode double effects. **Corrected in round 1 (C2):** the statement first written here, that the production bundle has no StrictMode, was wrong: `ui/src/main.tsx` wraps the root in `<StrictMode>`, and the committed bundle carries it. Production React runs each effect once; development replays it. Round 1 gave the opening read a cleanup and proved it in development mode ("Round 1 fixes", C2).
- A reply landing while "Close setup?" is open, and after Finish: not run as cases. After Finish the wizard is closed or on the Terminal step (`left`), so the reply is dropped.

## Cleanup

- Stopped by pid after reading each command line: the new-build server (8471), old-build server (8472), mutant server (8473), the real server (8474, its uv parent too), `serve.py` (8477), `slowproxy.py` (8478). No listener left on 8470 to 8479. Closed both of my preview tabs.
- Deleted the throwaway homes (`home-new`, `home-old`, `home-mut`, `home-real`, `home-pytest`). The instruments, results, `old-src`, `mut-src` (the last mutant's build) and screenshots stay under `~/.review-runs/2026-11-21-wizard-opening-read/`.
- `ui/node_modules` in the worktree is a symlink to the main checkout's; git does not list it, and it was never staged.

## Lead's round 0 change (after the answers on the two spec questions)

**What the lead decided.** (1) Remove the "no start sent" half (Mii_start, equivalent); record it under rule 2 in spec.md. (2) "Left stays left" accepted, its trade-off recorded above as residue. (3) BACKLOG keeps the branch name.

**What I changed, and a lint failure on the way.**
- `6f411a6`: the check became `if (!adopt || status !== null) return;` with the comment "no accepted read of this step's own yet. That is enough, since a start needs one too: the cards and the pick come from that read"; spec.md rule 2 has the lead-decision line.
- `npm run lint` then failed: `react-hooks/set-state-in-effect`, "Avoid calling setState() directly within an effect" at the effect's `setWatching(true)`. With the ref read gone the React compiler's rule now analyses that effect; before, the `startGenRef.current` read had kept it from flagging it. My command did not stop on the failure, so `a809629` (that bundle) was committed with lint failing. CI would have failed on that SHA; I fixed forward rather than rewrite the branch.
- `1def075`: the step takes the reply while rendering (React's "adjust state when a prop changes" pattern), so there is still one guard: `if (adopt && adopt !== taken && status === null) { setTaken(adopt); setWatching(true); }`. An effect on `taken` sets the form (`onSetEnabled(true)`, `onSelectSize(setup_last_model)`). Watching is true in the render that receives the reply; at mount, as before, it is true from `useState`. `onRunning` still has one call site (`OnboardingWizard.tsx:775`). `c1d9be0`: rebuilt bundle `index-CJbYAiX1.js`.

**Results on `index-CJbYAiX1.js`** (new empty HOME, port 8471, nothing else running):
- Full harness: **31 of 31 pass** (`results/r0b-final-all.json`): T1 to T13 and their variants, TG, T4v2, R3C1, R3C2, L3, LF3, LR2, L1A, L1B, L1C, L1D.
- Mutants, rebuilt into the separate package on 8473 and restored with `git checkout` after each build:

| Mutant | Guard removed | Killed by | What the failing case saw |
|---|---|---|---|
| **Mi** (i) | "left: drop" | **L1B** (`results/r0b-Mi.json`) | 2 s after the late reply: title "Local transcription", picked `small`, S14, instead of Workspace; going Back then landed on the provider step. L1A, L1C, L1D, T5_late pass. |
| **Mii_status** (ii; now the whole check) | `status === null` removed: `if (adopt && adopt !== taken)` | **L1C**, **L1D**, **T5_late** (`results/r0b-Mii_status.json`) | L1C: picked `small` and S14 after the stale reply was taken. L1D: S13 line, Back `disabled`, "Setting up… [disabled]" and S12 after a refused start; Escape asked instead of closing. T5_late: S14 shown, and an extra status read. L1A, L1B pass. |
| **Miii** (iii) | hand-off to a mounted step: `if (showing) return;` | **L1A** (`results/r0b-Miii.json`) | After the reply: no S13, Back `enabled`, "Install now [disabled]"; Escape closed the wizard at once. L1B, L1C, L1D, T5_late pass. |

Mii (the whole check) and Mii_status are now the same mutant, so only Mii_status was run. L1D now kills it too: with the start half gone, the status check alone covers the refused-start ordering.

**Checks on `c1d9be0`:** `npm run lint`: no findings. `npm run build`: `index-CJbYAiX1.js`, the committed name. `git diff --exit-code -- src/anyscribe/web/static`: clean.

**Not re-run after this change:** the real download walk (it ran on `index-Bl10hv_a.js`, whose reload path, the never-shown branch with acceptance at mount, is the same logic now; the harness's R3C1, T5, T6 and T13 cover that path on the new bundle). pytest, ruff and the docs checks were not re-run: no Python or user docs changed since they passed.

**Cleanup:** stopped by pid after reading each command line: 8471 (pid 1687867), `serve.py` 8477 (1687868), 8473 (1712849); no listener on 8470 to 8479; closed my preview tab; deleted `home-new2` and `home-mut2`.

## Round 1 fixes

Fixer: Claude Opus 5.5 (Agent tool). Branch `fix/wizard-opening-read`, base `13944d6` (checked with `git rev-parse --short HEAD` before editing). The fix plan (`fix-plan-r1.md`) set every choice below. C3 was the lead's.

Commits:
- `25c2f81` Setup wizard: drop a late opening reply only once the step heard something newer (C1/F1); spec.md rule 1 records the lead decision
- `2ca1ece` Setup wizard: the opening status read is cancelled when its effect is cleaned up (C2)
- `a333637` Rebuilt bundle `index-DdNfqDJq.js` (lint, build and the static diff check run first; static diff clean after)
- `1fbc25b` Records: BACKLOG's L1 line, the wave 2 API key line, the journal (F3)
- this section's commit

Instruments (outside the repo, not committed), in `~/.review-runs/2026-11-21-wizard-opening-read/instruments/`:
- `harness.js` has a new outcome, `gate`. The answer is held until `__openGate(name)`, so two replies can land in the same moment. The previous copy is `harness.r0.l1.js`.
- `l1-cases.js` adds L1E, L1F, L1G, L1H, L1S and L1X.
- `strict-cases.js` (SM1, SM2) runs in development mode only.
- `mutate.py` adds Mh, Mhold, Mshown, Mc2, Mlive and Mheard_start. Mii_status is kept, with the same text.
- `devcfg/vite.dev.config.mjs` serves the worktree's `ui/` through Vite's dev server on 8476. It proxies `/api` to my own server on 8471, not the config's 8457.

Old build for "fails before": `8d53ebc` (`index-CJbYAiX1.js`), from `git archive` into `old-8d53ebc/`, on 8472. New build: the worktree on 8471 (`index-DdNfqDJq.js`). Each server had a new empty HOME and ran with `--local-only`.

### C1 / F1: drop a reply only when something newer spoke. FIXED (`25c2f81`)

**Changed** (`OnboardingWizard.tsx`):
- The three-state ref is now two refs:
  - `localShownRef`: the local step was ever asked for. It is set inside the `setStep` wrapper, as before.
  - `heardRef`: the step heard something newer than the reply.
- `heardRef` is set by one stable callback, `onHeard`. As first built, the step called it in three places (the lead later removed the last two as equivalent; see "Lead's removal of the three equivalent spots"):
  - in the tick's accepted branch, right after `setStatus(s)`;
  - in `checkFfmpeg`, after `setStatus(s)`;
  - in `handleStartSetup`, before the start is sent (after `if (!selected) return`).
- `onHeard` touches only the ref. `watched` and `confirmClose` still have the step as their only writer, and `onRunning` still has one call site.
- The opening reply handler, when the reply says `setup_running`:
  - **heard:** drop it.
  - **never shown:** as before (set the form, hand the reply over, route).
  - **otherwise:** `setAdopt(reply)` only. The form and the route are untouched. A mounted step takes it while rendering; if the person is elsewhere, the step's next mount takes it, with `useState(adopt !== null)` and the same render-time take.
- Back and `goWorkspace` still clear the reply.
- The step keeps its one guard, `if (adopt && adopt !== taken && status === null)`. Its comment now says what it covers: a read accepted in the same render as the hand-off.
- spec.md rule 1 has the round 1 lead-decision line.

**Why no start can come between a hand-off and its take within one mount (plan item 4).**
- The take runs while rendering, in the render that receives the new `adopt`. React cannot run a click handler between `setAdopt` and that render's own body.
- A start sent before the hand-off calls `onHeard()` first, so the shell drops the reply instead of handing it over.
- A start sent after the take finds the step already watching. The start button is disabled while `busy`.
- On a second visit, where `selected` survives with `status === null`, the same holds. A start there sets `heardRef` before its request goes out.

**New cases, on 8d53ebc and on the new build** (`results/r1-old-l1.json`, `results/r1-new-l1.json`; all pass again in `results/r1-final-all.json`):

| Case | Sequence | 8d53ebc | New build |
|---|---|---|---|
| **L1E** (C1's sequence) | Opening reply (running Small) 7 s late. Local step with every read failing; Back; return; reads still failing; the reply lands. | **FAIL**: after the reply, no S13 line, Back `enabled`, "Install now [disabled]", S12. Escape gave `{"dialogOpen":false,"flag":null}`. | PASS: watched; Escape, backdrop and Skip each ask first (Keep setting up focused); flag `null`; Back is off; reads come back naming no model and the selected card is `small`; Close setup closes with the flag `null`. |
| **L1F** | The reply (4 s late) lands while the person is on Provider after a Back; they return. | **FAIL**: on return, not watched (Back `enabled`). Escape closed at once. | PASS: watched on the first snapshot after the return (150 ms); the same closing checks and the `small` card. |
| **L1G** | First visit: an accepted not-running read, Whisper Base picked. Back; return with failing reads; the reply lands. | pass (its "left" rule drops it too) | PASS: dropped. Not watched, Back enabled. When reads come back, `base` is still picked. Escape closes at once, flag `null`. |
| **L1H** | First visit: a refused start (500) after its accepted read. Back; return; the reply lands. | pass (same reason) | PASS: dropped. Not watched, `base` still picked, Escape closes at once. |
| **L1S** (for the step's guard) | First visit. The opening reply (running Small) and the step's first read (not running) are held at a gate and released together; both settle within 5 ms of each other. | pass | PASS: not watched, Back enabled, no red alert. Escape closes at once. |

The plan asked for each new case to fail on 8d53ebc. L1G and L1H cannot: 8d53ebc's "left: drop" rule drops those replies too, for a different reason. They are there to catch the new `heardRef` guard (Mh below), not a defect in the old build. L1S tests a guard 8d53ebc already had.

**Mutants** (each built into a separate copy of the package on 8473, with the worktree source restored by `git checkout` after each build):

| Mutant | Change | Killed by | What the failing case saw |
|---|---|---|---|
| **Mh**: heardRef's drop | `if (!live \|\| !s.setup_running) return;` | **L1B**, **L1G**, **L1H** (`results/r1-Mh.json`) | L1G: the second visit watched a stale reply (S13 line, Back `disabled`, "Setting up… [disabled]"). When reads came back, `small` was picked and S14 showed. L1H: the same. L1B: after Back from Workspace, the step took the held stale reply, `small` was picked, and S14 showed. L1A, L1C to L1F, L1S, L1X, T5_late and R3C1 pass. |
| **Mii_status**: the step's `status === null` | `if (adopt && adopt !== taken)` | **L1S** (`results/r1-Mii_status.json`) | With both replies landing in the same moment: S13 line, Back `disabled`, "Setting up… [disabled]", `small` picked. Escape asked first instead of closing. Every other case passes, so this guard is not equivalent: L1S is the ordering only it covers. |
| **Mhold**: hold for the next mount | the reply is handed over only if the step is on screen; otherwise dropped | **L1F** (`results/r1-Mhold.json`) | On return: no S13 line, Back `enabled`, "Install now [disabled]". Escape closed at once. Every other case passes. |
| **Mshown**: the whole hand-off after the step was shown | `if (localShownRef.current) return;` | **L1A**, **L1E**, **L1F** (`results/r1-Mshown.json`) | Each: not watched after the reply or the return, and Escape closed at once. |
| **Mheard_start**: the start no longer reports heard | `onHeard()` removed from `handleStartSetup` | **survives**: L1B, L1D, L1H, R3C2 pass (`results/r1-Mheard_start.json`) | **Equivalent, not a weak test** (traced below). **Removed by the lead's decision** (`aaf76f8`). |

Why Mheard_start is equivalent: a start needs `selected`. `selected` gets a value in one of two ways:
- From an accepted read on some visit: the recommendation, a card click or `onPresetSize`, all of which need `status`. That read already called `onHeard`.
- From a hand-off the step took: the never-shown branch, or a held reply taken at mount. The step then watches, the start button stays disabled, and Back is off until an accepted read ends watching. That read calls `onHeard`.

So `heardRef` is always true before any start, and the start's own call is never the one that sets it. The same trace covers `checkFfmpeg`'s call: "Check again" exists only when `status` shows ffmpeg missing, so a read was already accepted. I did not build that mutant. **Both calls were removed by the lead's decision** (`aaf76f8`). The lead checked the trace against the code: a pick without an accepted read comes only from the opening reply's form write or a taken hand-off, and both leave the step watching; the ffmpeg notice renders only once `status` is set.

### F2: a real walk on the bundle that ships. DONE

- **Bundle:** `index-DdNfqDJq.js`, committed in `a333637`. The page loaded it from the real server, as the page's own script URL shows.
- **Server:** the worktree's code. `HOME` was a new empty folder. Port 8474, `--local-only`. Downloads went through `slowproxy.py` at 200 kB/s per connection.
  - The server ran in a uv overlay environment on top of the main venv, with `faster-whisper`, `av<19` and `onnx-asr` added. I warmed that environment first without the proxy. Nothing was installed into the main venv: `import faster_whisper` there still fails.
- **Real clicks:** Let's go, On this computer, More models, Whisper Tiny, "Download Whisper Tiny (75 MB)". The server then reported `setup_running: true`, `tiny`, 0.9%.
- **Reload mid-setup:** the wizard opened on Local transcription. It showed "Back is off until setup finishes. Skip for now asks first.", "Downloading Whisper Tiny… 8.3%" and "Setting up…"; Back was disabled, Whisper Tiny was selected and the flag was `null` (`screens/r1-real-reload-watched-DdNfqDJq.png`).
- **Escape asks first:** I clicked the dialog title to focus the page, then pressed the real Escape key. "Close setup? The download keeps going…" opened, focus was on Keep setting up and the flag was `null` (`screens/r1-real-reload-escape-asks-DdNfqDJq.png`, opened and checked).
- **Keep setting up keeps it:** a real Enter on the focused button hid the box. The wizard stayed open and watched, at 15.5%, with the flag `null`.
- The download finished (`setup_outcome: set_up`, `tiny` runnable), and the page moved on to Workspace by itself.
- **Disk:** `df -h ~` showed 30 GB free before and after. The throwaway home (75 MB model, 462 MB uv cache) is deleted.

### C2: the opening read gets a cleanup. FIXED (`2ca1ece`)

**Changed:** the opening effect now makes its own `AbortController` and passes it to `limited`, and keeps a `live` flag that its `.then` checks first. The cleanup sets `live = false` and aborts.

**Proof, by harness case (production bundle) and in development mode (StrictMode):**
- **L1X** (production bundle): the wizard opens with the opening reply 3 s late, and Skip for now closes it at 0.5 s. The opening request ended `AbortError` less than 1.5 s after it was sent.
  - Under mutant **Mc2** (cleanup removed): it was `answered 200` at 3245 ms (`results/r1-Mc2.json`). **Killed by L1X.**
  - On 8d53ebc: `answered 200` too (`results/r1-old-l1.json`).
- **SM1 and SM2**, under Vite's dev server, where `<StrictMode>` replays the opening effect (`results/r1-dev-strict.json`):
  - Both show the read sent twice at the same moment: A (delayed 3 s) and B.
  - **SM1** is Sol's order: A says running Small, and the newer B says running Base. A was `AbortError`, B `answered 200`. After A's time had passed, Whisper Base was still the selected card.
  - **SM2**: B says not running, and A (running Small) is older. A was `AbortError`. The wizard stayed on Welcome.
  - With **Mc2** applied to the source the dev server serves (`results/r1-dev-strict-Mc2.json`):
    - SM1 fails: A `answered 200` at 3.3 s, and the step took it. Picked `small`, "Downloading Whisper Small… 30%".
    - SM2 fails: A routed a Welcome wizard to Local transcription. Picked `small`, and S14 after the next read.
  - The source was restored with `git checkout` straight after.
- **Mutant Mlive** (only `live = false` removed, the abort kept): **survives** L1X, L1A and R3C1 (`results/r1-Mlive.json`).
  - It is equivalent in practice. Once the cleanup aborts, `limited`'s promise rejects and the `.then` never runs. `live` matters only if the request had already settled but its `.then` had not yet run when the cleanup ran, which is a window of a few microtasks.
  - StrictMode's replay runs mount, cleanup and mount within one commit, before any reply can arrive. A wizard closed by a click unmounts in that click's task.
  - **Removed by the lead's decision** (`aaf76f8`). The `AbortController` and `ctl.abort()` in the cleanup stay.
- **proof.md corrected:** "What I could not prove" no longer says the bundle has no StrictMode. `main.tsx` wraps the root in it; production React runs each effect once.

### F3 and the records. DONE (`1fbc25b`)

- **BACKLOG.md, the L1 line**, now ends "…so one Escape or Skip can close without the warning while a download runs (review L1, 2026-11-20); Done in #PR: a late reply is dropped only once the local step has heard something newer (an accepted read or a start); otherwise the step takes it." `#PR` is literal, for the lead to fill in.
- **BACKLOG.md**, an unticked wave 2 line under R2L1, verbatim from the plan: the late opening reply on the API key step.
- **Journal, Follow-up 2:** the rule is now "heard". Round 1 gets one paragraph on why the rule changed. The proof line names the Back-and-return and same-moment cases and the real walk.
- **spec.md:** the round 1 lead-decision line under rule 1 (in `25c2f81`).

### Full harness on the final bundle `index-DdNfqDJq.js`: 37 of 37 pass (`results/r1-final-all.json`)

T1, T1_500, T2, T3, T4, T4_notRunning, T4_refused, T5, T5_late, T6, T7, T8, T9, T10, T11, T12, T12b, F4, F1, T13, TG, T4v2, R3C1, R3C2, L3, LF3, LR2, L1A, L1B, L1C, L1D, and the new L1E, L1F, L1G, L1H, L1S, L1X. No existing case changed.

### Checks on the final commit

`npm run lint`: no findings. `npm run build`: `index-DdNfqDJq.js`, the committed name. `git diff --exit-code -- src/anyscribe/web/static`: clean. pytest was not run: no Python changed in round 1, as the plan says.

### Where the plan is wrong, or worth a second look

1. "Each failing on 8d53ebc" cannot hold for the heard-on-first-visit and refused-start cases (L1G, L1H). 8d53ebc drops those replies too, by its "left" rule. They pass there and serve as the kill cases for the new `heardRef` guard (Mh).
2. The refused-start case cannot isolate "a start" as what was heard. A start needs a pick, and on a first visit the pick needs an accepted read, which has already set heard. The start's own `onHeard()` call is an equivalent mutant (Mheard_start). **Removed by the lead**, together with `checkFfmpeg`'s call.
3. The `live` flag is equivalent in practice once the abort is there (Mlive). **Removed by the lead.**

### Cleanup

- Stopped by pid after reading each command line:
  - 8471 (pid 1731626), 8472 (1731627), `serve.py` on 8477 (1731628);
  - the mutant server on 8473 (1745532) and the Vite dev server on 8476 (1804062);
  - the real server on 8474 (1845604, with its uv parent 1845592) and `slowproxy.py` on 8478 (1845591).
- No listener is left on 8470 to 8479. My preview tab is closed.
- Deleted the throwaway homes (`home-r1new`, `home-r1old`, `home-r1mut`, `home-r1real`).
- Left in the run folder: the instruments, results, screenshots, `old-8d53ebc/`, `mut-src/` (the last mutant's build), `devcfg/` (config plus a node_modules symlink) and `wizard-with-c2.tsx` (a working copy).

### Lead's removal of the three equivalent spots (round 1, after the fix)

The lead's decision follows the house rule that a guard no test can tell apart is removed. It is recorded in fix-plan-r1.md's C1/F1 section.

**Commits:**
- `aaf76f8` removes the opening effect's `live` flag; the `AbortController` and the cleanup `() => ctl.abort()` stay. It also removes `onHeard()` from `handleStartSetup` and from `checkFfmpeg`. The shell's comment, the `onHeard` prop's doc comment and the step's comment now say "heard" means the step accepted a status read of its own on any visit, since a start needs one first. `onHeard()` has one call site left, the tick's accepted branch.
- `9449ff8` updates the records: a line in fix-plan-r1.md, spec.md's round 1 line, the journal's Follow-up 2 and the BACKLOG L1 line. None of them says "a read or a start" any more; I checked with `grep`.
- `e17d174` is the rebuilt bundle, **`index-CDPOZTVX.js`**. Lint and build ran first, and the static diff was clean after.
- This section's commit.

**Full harness on `index-CDPOZTVX.js`: 37 of 37 pass** (`results/r1b-final-all.json`). The server had a new empty HOME, port 8471, and nothing else running.

**Mutants on the final code** (built into the separate copy of the package on 8473; the worktree source was restored with `git checkout` after each build). The mutation strings for Mh and Mc2 were updated to the new code shape.

| Mutant | Killed by | What the failing case saw |
|---|---|---|
| **Mh** (heardRef's drop) | **L1B**, **L1G**, **L1H** (`results/r1b-Mh.json`) | L1G and L1H: the second visit watched a stale reply (S13 line, Back `disabled`). When reads came back, it showed S14 with `small` picked. L1B: after Back from Workspace, S14 with `small` picked. |
| **Mii_status** (the step's `status === null`) | **L1S** only (`results/r1b-Mii_status.json`) | Both replies released in the same moment: S13 line, Back `disabled`, "Setting up…"; Escape asked instead of closing. |
| **Mhold** (holding for the next mount) | **L1F** (`results/r1b-Mhold.json`) | On return: not watched, Back `enabled`; Escape closed at once. |
| **Mshown** (no hand-off at all once shown) | **L1A**, **L1E**, **L1F** (`results/r1b-Mshown.json`) | Not watched after the reply or the return; Escape closed at once. |
| **Mc2** (no cleanup) | **L1X** (`results/r1b-Mc2.json`) | The opening request was `answered 200` at 3220 ms after the wizard had closed, where it should have ended `AbortError`. |

**Checks:** `npm run lint` found nothing. `npm run build` produced `index-CDPOZTVX.js`, the committed name. `git diff --exit-code -- src/anyscribe/web/static` was clean. `git diff --check 13944d6..HEAD` was clean.

**Not re-run after this removal:**
- The real walk (F2) at first. It was then run at the lead's request; see "Real walk on the shipping bundle" below.
- The development-mode StrictMode cases (SM1, SM2). With the `live` flag gone, the first request is still aborted by the cleanup, which is what those cases asserted.

**Cleanup:** I stopped 8471 (pid 1912019), `serve.py` on 8477 (1912020) and the mutant server on 8473 (1928842) by pid after reading each command line. No listener is left on 8470 to 8479. My preview tab is closed, and `home-r1bnew` and `home-r1bmut` are deleted. `df -h ~` shows 30 GB free.

**Real walk on the shipping bundle (F2's bar), at `25078b1`, bundle `index-CDPOZTVX.js`.** No harness and no fakes. No code changed for this walk.
- **Server:** the worktree's code. `HOME` was a new empty folder. Port 8474, `--local-only`. The model download went through `slowproxy.py` at 200 kB/s per connection. The server ran in a uv overlay environment on the main venv, with the engines added; I warmed that environment first without the proxy. The main venv is untouched: `import faster_whisper` there still fails.
- **The page loaded the shipping bundle:** its own script URL is `/assets/index-CDPOZTVX.js`.
- **Real clicks:** Let's go, On this computer, More models, Whisper Tiny, "Download Whisper Tiny (75 MB)". The server then reported `setup_running: true`, `tiny`, 5.6%.
- **Reload mid-setup:** the wizard opened on Local transcription. It showed "Back is off until setup finishes. Skip for now asks first.", "Downloading Whisper Tiny… 10%" and "Setting up…"; Back was disabled, Whisper Tiny was selected and the flag was `null`. Screenshot: `screens/r1c-real-reload-watched-CDPOZTVX.png` (10.9% at capture).
- **A real Escape opens "Close setup?":** I clicked the dialog title to focus the page, then pressed the real Escape key. "Close setup?" opened, focus was on Keep setting up, the dialog stayed open and the flag was `null`.
  - The screenshot of this first box came out blank: the capture caught the dialog before its text painted.
  - I pressed Enter (Keep setting up) and a real Escape again; the state was the same (box open, focus on Keep setting up, flag `null`). After a forced repaint the capture was clean: `screens/r1c-real-escape-asks-CDPOZTVX.png`, at 30.8%.
- **Keep setting up keeps it:** both real Enter presses on the focused Keep setting up hid the box. The wizard stayed open and watched: the S13 line, "Setting up…", the flag `null`, and progress at 20.6%, then 33%, 35.2% and 37.5% on later reads.
  - No clean screenshot of this state exists. Captures after the box closed kept the dialog's top half unpainted (`screens/r1c-real-after-keep-unpainted-CDPOZTVX.png`, kept only as a record of the artifact). The evidence for this step is the DOM reads above.
- The download finished (`setup_outcome: set_up`, `tiny` runnable), and the page moved on to Workspace by itself with the flag `null`.
- **Cleanup:** I stopped the real server (pid 1935173, with its uv parent 1935160) and `slowproxy.py` (1935159) by pid after reading each command line. No listener is left on 8470 to 8479. My preview tab is closed. The throwaway home (75 MB model plus the uv cache) is deleted.
- **Disk:** `df -h ~` showed 30 GB free before and after (219G total, 178G used).

## Lead-made change after the round 2 re-check (R2C1, unreviewed, lead-verified)

**The change.** The owner chose a lead-made fix, reported as lead-verified rather than reviewed. It is the lead's own:
- `294fb9e`: `askOrClose` also asks when `adopt && step !== "offline_opt_in"`. A running reply held for the local step makes closing ask on any other screen.
- `a184b18`: bundle `index-B5rC99Gz.js`.
- `1a09db2`: records.

This section is the test evidence only; no code under `ui/src` or `src/` changed for it. Branch checked at `1a09db2` before starting.

**Bundles.**
- Old: `index-CDPOZTVX.js`, from `4b7232e`, unpacked with `git archive` into `old-4b7232e/` and served on 8472.
- New: `index-B5rC99Gz.js`, the worktree at `1a09db2`, served on 8471.
- Each server had a new empty HOME and ran with `--local-only`.
- The cases are in `~/.review-runs/2026-11-21-wizard-opening-read/instruments/r2-cases.js` (not committed).

**What the cases assert.**
- Where the screen allows it, closing is tried three ways: Escape, a backdrop click and Skip for now. Each must open "Close setup?" with focus on Keep setting up, and the dismissed flag must stay `null`.
- Nothing may change while the box is open or after it: the title, the "Step N of M" counter and the API key field's value must all stay the same. The counter shows the provider (cloud is "of 4", local is "of 3"). On All set, the whole summary must be unchanged.
- Close setup then closes the wizard with the flag `null`.

| Case | Sequence (the opening reply, running Whisper Small, is held until after the person moves on) | `index-CDPOZTVX.js` (old) | `index-B5rC99Gz.js` |
|---|---|---|---|
| **R2P**, must ask | Local step with failing reads, Back to Provider; the reply (4 s late) lands on Provider | **FAIL**: Escape closed at once, `{"dialogOpen":false,"flag":null}` | PASS: Escape, backdrop and Skip each ask; flag `null`; still "How should anyscribe transcribe?", "Step 1 of 3"; Close setup closes, flag `null` |
| **R2K**, must ask | Cloud path (Sarvam key typed), the optional local step with failing reads, Back to API key; the reply (5 s late) lands there | **FAIL**: Escape closed at once | PASS: all three ask; still "Add your API key", "Step 2 of 4", key `sk_fake_sarvam_key_0000` kept; Close setup closes, flag `null` |
| **R2W**, must ask | Cloud path, local left off, "Skip, next" before any accepted local read (checked: 0 accepted status reads); the reply (5 s late) lands on Workspace | **FAIL**: Escape closed at once | PASS: all three ask; still "Workspace location", "Step 4 of 4"; Close setup closes, flag `null` |
| **R2D**, must ask | The R2W sequence, then Next to All set; the reply (6 s late) lands there | **FAIL**: Escape closed at once | PASS: Escape and backdrop ask (no Skip on this screen, checked); flag `null`; still "All set"; summary unchanged (Sarvam, no "On this computer", no offline model); Close setup closes, flag `null` |
| **R2N1**, must not ask | The reply is held on Provider; the person returns and the step takes it (S13 line, Back off); then the real server's not-running read ends watching (S13 line gone, Back enabled, S14) | pass | PASS: Escape closes at once, flag `null` |
| **R2N2**, must not ask | The step's own read is accepted first (heard); Back to Provider; the reply lands later and is dropped | pass | PASS: Escape on Provider closes at once, flag `null` |

The old bundle never reached Skip in the four "must ask" cases, because Escape had already closed the wizard. R2C1's report traces that Skip there sets the flag.

**Full harness on `index-B5rC99Gz.js`: 43 of 43 pass** (`results/r2-final-all.json`). That is the 37 cases of round 1, LR2 among them, plus R2P, R2K, R2W, R2D, R2N1 and R2N2. Results: `results/r2-new.json` and `results/r2-old.json`.

**Mutant Mstep.** Only the `step !== "offline_opt_in"` part is removed: `watched || (adopt) ? ask : close`. It was built into the separate package on 8473 as `index-DYCsB2gr.js`, and the worktree source was restored with `git checkout`. **Killed by R2N1 and T5** (`results/r2-Mstep.json`):
- **R2N1:** after the real not-running read ended watching (S14, Back enabled), Escape opened "Close setup?" instead of closing.
- **T5:** the same on the never-shown path. The opening reply routed, the step's read said not running, and S14 showed; Escape still asked.
- Both happen because `adopt` stays set while the person is on the local step after the step took it.
- R2P, R2K, R2W, R2D, R2N2, T5_late and T13 pass under the mutant.
- So the step check is not equivalent: without it, a setup that has visibly ended still asks before closing.

**One concern for the lead (traced, not run; no code changed).**
- **Where:** the Mac app's Terminal step, which comes after Finish (`setStep("terminal")` when `offerTerminal` is set).
- **How it is reached:** a reply held on Workspace or All set is still in `adopt` after Finish, because Finish does not clear it. The step is now `"terminal"`, which is not `"offline_opt_in"`, so the held-reply condition is true.
- **What happens:** Escape or a click outside calls `offerTerminal()` and then `askOrClose(true)`, which now opens "Close setup?".
  - That box says "Your choices on these screens are saved only when you click Finish", although Finish has already saved them.
  - Close setup calls `dismiss(false)`, where this path used `dismiss(true)` before.
  - A second Escape only hides the box, and a third calls `offerTerminal()` again.
- **Not a trap:** Close setup and the Terminal flow's own Done still close the wizard.
- **Reach:** only the Mac app, and it needs the same slow-server sequence as R2W or R2D followed by Finish.
- **Possible fixes, the lead's call:** exclude `"terminal"` (and `"done"`?) from the held-reply condition, or clear `adopt` at Finish.
- **Not run:** the web harness cannot open the Mac app's Terminal step, so this has no harness case.

**Cleanup.**
- Stopped by pid after reading each command line: 8471 (1974113), 8472 (1974114), `serve.py` on 8477 (1974115) and the mutant server on 8473 (1986875).
- No listener is left on 8470 to 8479, and my preview tab is closed.
- Deleted `home-r2new`, `home-r2old` and `home-r2mut`.
- `df -h ~` shows 30 GB free.
- Only proof.md is committed.

### Follow-on: Finish forgets a held reply (the Terminal step)

**The lead's change**, made in response to the Terminal-step concern above:
- `1395710`: `setAdopt(null)` on a successful save, before `setStep("terminal")`.
- `cd988eb`: bundle `index-CsnycLZe.js`.

Test only. The branch was checked at `cd988eb` before starting, and no code under `ui/src` or `src/` changed.

**How it was run.**
- The script is `~/.review-runs/2026-11-21-wizard-opening-read/instruments/mac_terminal.py` (not committed), run with `/usr/bin/python3` and Playwright.
- Before the page loads, it injects the 2c-ui review's `checks/stub.js` (`window.anyscribeDesktop`: Mac, Terminal not yet asked, no old launcher) and this run's fetch `harness.js`.
- The harness holds the opening read for 7 s and then answers "running Whisper Small". Every other local status read fails. The harness records the onboarding save without sending it.
- Each bundle ran on its own engine, with a new empty HOME and `--local-only`:
  - new: the worktree at `cd988eb`, `index-CsnycLZe.js`, on port 8471;
  - old: `a184b18`, from `git archive`, `index-B5rC99Gz.js`, on port 8472.

**Sequence.**
1. Cloud path (OpenAI, test key), the optional local step with local left off, then "Skip, next" before any accepted local read (checked: 0 accepted status reads).
2. The held running reply lands on Workspace.
3. Next to All set, where Escape is pressed: it must ask first.
4. Keep setting up, then Finish: the save is recorded and the Terminal step ("One last thing") shows.
5. Escape on the Terminal step.

| Check | `index-B5rC99Gz.js` (a184b18) | `index-CsnycLZe.js` (cd988eb) |
|---|---|---|
| All set, before Finish: Escape asks first (focus on Keep setting up, flag `null`) | pass | **PASS** |
| Finish: the save is recorded (provider `openai`); the Terminal step shows | pass | **PASS** |
| Terminal step: Escape opens no "Close setup?" | **FAIL**: `{"open":true,"title":"One last thing","s11":true,"focus":"Keep setting up","flag":null}` | **PASS** |
| offerTerminal is answered once: the stub recorded exactly `firstLaunch.mark("terminalAsked")` | pass | **PASS** |
| The wizard closes with the flag `"1"` (`dismiss(true)`, as before R2C1) | **FAIL**: still open, flag `null` | **PASS** |

Results: `results/mac-terminal-CsnycLZe.json` and `results/mac-terminal-B5rC99Gz.json`.

**Full harness on `index-CsnycLZe.js`: 43 of 43 pass** (`results/r2b-final-all.json`). This includes R2P, R2K, R2W, R2D, R2N1 and R2N2.

**The 2c-ui check kit's wizard last-step checks.**
- I ran a copy of `checks/check_ui.py` from the run folder, `checkui/check_ui.py` (not committed), against this worktree's code and bundle: `--only wizard,wizard_escape,wizard_browser --no-shots`.
- The copy differs from the original in three lines only:
  - `WORKTREE` is pinned to this worktree;
  - engine ports come from 8475, 8476, 8478 and 8479 instead of any free port;
  - engines start with `--local-only`.
- Its temporary homes went under the run folder, and it removed them itself.
- **5 passed, 0 failed:**
  - "new person: the wizard, not the separate card";
  - "Terminal is the wizard's last step, titled One last thing (F13)";
  - "Skip for now marks and closes the wizard, no second card";
  - "C6: Escape on the wizard's Terminal step is Skip for now: marked, nothing turned on";
  - "browser: Finish closes the wizard (no Terminal step)".
- These checks walk with a real "not running" status, so they cover the Terminal step's normal path. The held-reply path is the `mac_terminal.py` run above.

**Cleanup.**
- Stopped by pid after reading each command line: 8471 (2000249), 8472 (2000250) and `serve.py` on 8477 (2000887). `check_ui.py` stopped its own four engines by pid.
- No listener is left on 8470 to 8479, and my preview tab is closed.
- Deleted `home-r2bnew` and `home-r2bold`.
- `df -h ~` shows 30 GB free.
- Only proof.md is committed.
