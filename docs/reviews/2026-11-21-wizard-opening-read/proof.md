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
2. **A second visit to the local step.** Rule 1 names never shown, showing and left, but not "left, then shown again". I made `left` final: a reply landing on a second visit is dropped, because the first visit's reads and any start are newer than it. Reading "showing now" literally would hand it to the new mount, which has not read yet, and a stale "running" could then start watching and end in a false "Setup didn't finish". **Accepted by the lead as built, with this residue: if every read on the first visit failed, the old reply no longer helps a second visit.** The step's own reads still show the running download once they get through.
3. **Variant C failed on the old build too**, by overwriting the pick, not by watching. The spec framed C as a guard check; it is also a defect the old code had.
4. **"Has been shown" is set when the step is asked for**, in the `setStep` wrapper, not after React renders it. An effect would leave a gap between a `setStep` from a status callback and the commit in which a reply could still be routed by the old value.

## What I could not prove

- The real run used the Linux preview browser only; no Mac or Windows, no screen reader.
- React StrictMode double effects: the production bundle has no StrictMode, and I did not run the dev server. Reasoned only: the opening effect's second read would land while `showing` and be handed to the step, which takes it only if it has not read yet, the same reply twice.
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
