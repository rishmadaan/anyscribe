# Proof: closing asks first (wave 1 lock follow-up), round 0

Implementer: Claude Opus 5.5 (Agent tool). Branch `feat/onboarding-wave1-lock`, base `96b76bc` (checked with `git rev-parse HEAD` before editing).

Commits:
- `c5b6a0a` Setup wizard: closing asks first during a download, never locked (rules 1 to 11, rebuilt bundle `index-CBp6eUC1.js`)
- `97c5c67` Records for closing asks first: changelog, backlog, troubleshooting, journal
- this file's commit

Raw evidence lives outside the repo in `~/.review-runs/2026-11-20-onboarding-wave1-lock/` and is not committed:
- `instruments/`: `harness.js` (the round 3 tab harness, adapted), `cases.js` (all cases; the lead's TG and T4v2 from `lead-gap.js` are merged in), `mutate.py`, `serve.py`, `slowproxy.py`, `diskwatch.sh`.
- `instruments/results/*.json`: every run, saved by the page itself (`all-1`, `M2`, `M5`, `M6g`, `M9s`, `restored`, `final-all`).
- `logs/resume-disk.log`: the real download, one line per second (bytes on disk, server progress). `logs/freeze-*.txt`: the venv before, with and after the engines.
- `screens/*.png`: each opened and checked for content before it is cited here.

## Instruments

- Harness server: `HOME=~/.review-runs/2026-11-20-onboarding-wave1-lock/home-a .venv/bin/python -m anyscribe ui --port 8491 --no-open --local-only`, my own T3 preview tab, `serve.py` on 8497 for the harness files and results.
- Harness (unchanged mechanics from round 3): wraps the tab's `fetch` for status, setup, log and save, each with a queue of outcomes (real, real with fields overridden, network failure, hang until aborted, a set HTTP answer, any of these delayed). The setup POST never reaches the server; Finish is recorded, not sent. Every request is logged with send and settle times.
- Adapted for this design: the screen reader looks for S13 as its own line, reports Skip for now, S11, S12, S14, where focus is, and where each red block sits (`aboveButtons` when its next sibling is the Back/start row). `fresh()` answers S11 with Close setup when Skip asks first.
- Case helpers: `watched` = S13 shown, Skip for now shown, Back disabled, start button "Setting up… [disabled]". `asked` = dialog still open, S11 shown, focus on "Keep setting up".

## Results: 24 of 24 cases pass on the committed bundle (`results/final-all.json`, also `all-1.json`)

| Case | What it drives | What it asserts now ("closing asks first") |
|---|---|---|
| T1, T1_500 | start 200, next status read fails (network / 500), then running | watched with no S12 after one failed read; checkbox on and off; no raw text; "Downloading Whisper Base… 25%"; Escape asks first (focus on Keep setting up); Keep setting up hides it; backdrop asks first; requests: setup 200, failed status, good status |
| T2 | start 409, read fails, another tab's Whisper Small running | watched, no "409"; adopts Small (card picked, "Downloading Whisper Small… 40%") |
| T3 | start 409, read says stopped and runnable | Workspace, no 409; requests: setup 409 then one good status read |
| T4 | start gets no answer, then running | watched, "…10%" |
| T4_notRunning | start gets no answer, server says not running, no outcome | S14 just above the buttons, Try again, not watched; Escape closes at once, flag unset |
| T4_refused | start answered 500 | "anyscribe couldn't start the setup. Click Try again; …" just above the buttons, no "500"/body; no status read after |
| T5 | wizard's read running, step's read not running (no outcome) | adopted, then the step's read ended it: S14 just above the buttons; not watched; Escape closes at once; exactly 2 status reads |
| T5_late | the wizard's running read lands 3 s late, after the step's own not-running read | nothing adopted, no red alert, Back enabled; Escape closes at once; 2 status reads |
| T6 | wizard's read running, step's reads fail ×3, then running | after two failures: S12 and still watched; Escape asks first; then progress 30%, S12 gone |
| T7 | watching, then 30 s of failed reads | S12, still watched, no live percent; 20 reads, one at a time (`maxInflight` 1); Escape asks first; Keep setting up; reads return: S12 clears, 60%; Skip asks first; Close setup closes, flag `null` |
| T8 | stopped and runnable, every log read fails | Workspace; every log request `TypeError` |
| T9 | one read hangs, then one fails | watched while hanging; hung read `AbortError` at 10000 ms; S12; recovers; `maxInflight` 1 |
| T10 | the ending read, then Next | stays on All set; no status read after the ending read |
| T11 | a read sent before Download, delayed 3 s, carrying an old error | watched, no old error; that read `AbortError` 101 ms after it was sent |
| T12 | restarted server: not running, no outcome, no error, only Tiny runs | S14 just above the buttons, Try again, never All set |
| T12b | same, with outcome `set_up` | the missing-part sentence ("Setup finished, but Whisper Base can't run yet…"), not S14 |
| F4 | setup ends needing a restart | no red alert; the banner ends with S15; no "Restart anyscribe, then open" |
| F1 | ffmpeg missing, Windows and Linux user agents (keep-list) | Windows: quit from the tray and reopen; Linux: "then click Check again" |
| T13 | Escape while reachable, Keep setting up, unreachable, backdrop, Close setup, Settings → Run setup wizard | asks first each time; Close setup closes with flag unset; reopens on the running download, watched, "…50%" |
| TG (lead's) | start answers after 3 s; Escape at 0.8 s, then backdrop | both ask first while the start is in flight; then watched with 25% |
| T4v2 (lead's) | the start hangs | watched at 3 s; Escape asks first; start `AbortError` at 10000 ms; then watched with 12% |
| R3C1 (new) | wizard's read running; the step's first read hangs, then reads fail | see rule 5 |
| R3C2 (new) | a running read lands during a 6 s start, then stopped-and-runnable reads | see rule 6 |

T4_hang (round 3) is replaced by the lead's T4v2, as in the previous review: its "no lock line during the start" expectation was already obsolete.

## Rule by rule

**Rule 1, never trapped. BUILT.** `disableClose={saving}` (`OnboardingWizard.tsx`, the Modal). Skip for now renders whenever `step !== "done" && !saving`, watched or not. Every case above checks `skipForNow` while watched. All set still has no Skip (it never had one; it has Finish and Back), which I read as outside "no download ever hides it".

**Rule 2, asks first while watched. BUILT.** `askOrClose = (persist) => (watched ? setConfirmClose(true) : dismiss(persist))` is what Escape, the backdrop (both through `Modal.onClose`) and Skip for now call. `watched` is the step's `busy` (watching, or the start request in flight). Not watched: T4_notRunning, T5, T5_late close at once on Escape with the flag unset.
- Mutant M2 (`false && watched`): **T1, TG, R3C1, T13 fail**, each with `{"dialogOpen":false,"flag":null}` right after Escape while watched (`results/M2.json`). Restored: all four pass (`restored.json`, `final-all.json`).

**Rule 3, the confirmation. BUILT.** S11 verbatim with "Keep setting up" (`autoFocus`) and "Close setup" (`dismiss(false)`). S11 hides by itself when the step stops being watched. Escape while S11 is open leaves it open (round 0; changed in round 1, LF3: Escape, and a click outside, now hide it, as Keep setting up does).
- F3-4, settled at 390 px: dialog scrolled to the bottom (`scrollTop` 842), real Escape key: `scrollTop` 0, focus on "Keep setting up", its box inside the dialog's visible area (`screens/s11-s13-escape-after-scroll-390.png`).
- Real Escape key and real Enter on the focused "Keep setting up" in the real walk (rule 12): S11 opened, then hid.

**Rule 4, one owner. BUILT.** The step's one effect: `const report = (w: boolean) => onRunning(w); report(busy); return () => report(false);`. `git grep -n "onRunning("` outside `docs/reviews`: one line, `ui/src/components/OnboardingWizard.tsx:734`. Round 3 machinery unchanged: one bounded read at a time (`limited`, 10 s), failures never end watching (T7, T9), the log read separately (T8), completion once (T10), no raw text (`rawText` empty in every snapshot).

**Rule 5, R3C1 adoption. BUILT.** The wizard's opening read, on `setup_running: true`, sets the form (local, on, `setup_last_model`), `setAdopt(true)` and routes; the step starts with `useState(adopt)`. `adopt` is cleared when the step is left (its Back and its Next), so a later visit does not reuse it; a late read that lands while the step is already mounted does not reach it (T5_late).
- R3C1 case, guarded: 0.5 s after routing, with the step's first read still `pending`: watched; Escape, backdrop and Skip each ask first (flag `null`); a click on Back does nothing. After the hung read (`AbortError` at 10001 ms) and one failure: S12, still watched; Escape and Skip ask first, Back still disabled; Close setup closes, flag `null`. Requests: wizard status `over → answered 200`, step status `hang → AbortError (10001 ms)`, `fail → TypeError`.
- Mutant M5 (`useState(false && adopt)`): **R3C1 fails**: before the step's first read, no S13, Back enabled, button "Install now", and Escape gives `{"dialogOpen":false}`. **T6 fails** the same way after S12 shows (Back enabled, Escape closes). T13 survives M5: its reopened step's own read answers "running" within 0.3 s, so it never depends on adoption (`results/M5.json`). Restored: R3C1, T6 pass.

**Rule 6, R3C2 ordering. BUILT.** `startGenRef` moves by one when the start request is sent and again when it settles (odd = in flight). A status read records it when sent; on its answer it may touch status or watching only if the value is unchanged and even. A read sent before the start settled, or landing during it, is ignored. After the start settles, `setWatching(true)` restarts the loop, so only reads sent afterwards can end it.
- R3C2 case, guarded: requests `status over+1000 → answered 200 @0` (Whisper Small running), `setup http200+6000 @100`, `status over → 200 @2826`, `status over → 200 @4568` (both stopped and runnable), `status over → 200 @6101`. At 5.3 s, with the start still `pending`: still on Local transcription, watched, Small not adopted. Then Workspace; the ending read was sent at 6101 ms, after the start settled at 6100 ms.
- Mutant M6g (guard always true): **R3C2 fails**: at 5.3 s the title is "Workspace location" while the setup request is still `pending`; the ending read was sent at 1272 ms, 4.8 s before the start settled (`results/M6g.json`). T11 survives M6g (its old read is aborted by the loop restart, the round 3 mechanism). Restored: R3C2 passes.
- Side effect, by design: while a start is in flight and no status has arrived yet, reads are ignored, so "Loading models…" stays until the start settles (10 s at most).

**Rule 7, Back during a download. BUILT.** Back stays `disabled={busy}`; S13 "Back is off until setup finishes. Skip for now asks first." is its own line under the header while watched (`screens/s13-watched-1440.png`). Every watched snapshot has `back: "disabled"`.

**Rule 8, S12. BUILT, fallback wording** (rule 12 not proven): "Can't reach anyscribe right now. If you closed it, open it again: this page then shows the download if it is still running, or a Try again button to start it again." Seen for real when I stopped my server mid-download (`screens/real-s12-server-stopped-1440.png`), and in the harness (`s12-unreachable-1440.png`, `s12-unreachable-390.png`).

**Rule 9, S14. BUILT, fallback wording**: "The setup stopped before it finished, because anyscribe was closed. Click Try again to start it again." Shown on the ending read when `setup_outcome` is null (no `setup_error`; that branch comes first), with the existing Try again button. A runnable model still advances.
- Mutant M9s (the S14 condition never true): **T12 fails** ("Setup finished, but Whisper Base can't run yet…" instead of S14) and **T4_notRunning fails** ("A part anyscribe needs … didn't install…"). Requests in both: the ending status read `answered 200`, no status read after (`results/M9s.json`). T12b passes under M9s and guarded, so S14 replaces the sentence only when there is no outcome. Restored: T12, T4_notRunning pass.
- Real: after my server restart mid-download, the restarted server's own answer gave S14 and Try again (`screens/real-s14-after-restart-1440.png`).

**Rule 10, F3-2. BUILT.** The `setupError` and `missing` blocks (S14, the missing-part sentences, the refusal sentence) render after the picker, immediately before the Back/start row; the progress line stays above the picker. `redPlace: ["aboveButtons"]` in T4_notRunning, T4_refused, T5, T12, T12b; `screens/s14-red-above-buttons-1440.png`, `-390.png`.

**Rule 11, F3-3. BUILT.** The RestartBanner's added sentence is S15 (F4). `LocalSetupNotes.tsx` needed no change: the sentence is the wizard's `children`.

**Rule 12, the resume claim. NOT PROVEN, so the fallback wording is used in S12, S14, troubleshooting and the changelog.** The real run:
- Engines installed into `.venv` for it with `uv pip install` (9 packages: av 18.1.0, ctranslate2 4.9.0, faster-whisper 1.2.1, flatbuffers 25.12.19, numpy 2.5.5, onnx-asr 0.12.0, onnxruntime 1.32.0, protobuf 7.36.2, tokenizers 0.23.3), so the setup skipped its install step. huggingface_hub 2.4.0 with hf_xet, the customer default.
- Server: `HOME=…/home-resume`, port 8492, `HTTPS_PROXY` through `slowproxy.py` (1 MB/s per connection; xet used several, about 2.7 MB/s). Real clicks: Let's go, On this computer, the Whisper Base card, "Download Whisper Base (140 MB)".
- 17:31:02.128: progress 35.6% (52,622,454 of 147,886,409 bytes). I stopped my server (pid read first). On disk: the weights file `d01c3014….dc0d0dfa.incomplete` = **0 bytes**; the whole cache 2,714,423 bytes (the five small files only).
- The page: two failed reads, S12 (real). A real Escape: S11 with focus on Keep setting up; a real Enter: hidden.
- 17:31:34: restarted on the same home and port. The page: S14 and Try again, from the restarted server's answer.
- Real click on Try again. 17:32:01: 0 of 0; 17:32:02.663: **0.6%** (835,398 of 145,217,532); 2.8%, 5.5%, 8.1% at the same rate as the first run. The download started again from zero.
- 17:33:15: finished, outcome `set_up`; the page moved on to Workspace; Whisper Base runnable.
- Why, from the library: `huggingface_hub/file_download.py`, `_download_to_tmp_and_move` writes each download to a process-unique `<name>.<uuid>.incomplete` opened with `"wb"`, and xet wrote nothing to it before the stop. The plain HTTP path (no xet) uses the same function; I traced it, I did not run it.

## Fixed strings

S11 to S15 appear verbatim in the committed bundle `index-CBp6eUC1.js` (one hit each), and the old strings ("Keep waiting", "Skip and Back are off", "this page picks the") have none. S11's full text was read from the page (`visibleText`) as written in the spec.

## Records

- `CHANGELOG.md` Unreleased: the W6 entry now describes closing asks first, never locked, S12 and S14.
- `BACKLOG.md`: the W6 follow-up and "A way out of a slow download" ticked; the W6 line says the hard lock was replaced; wave 2 lines for the conftest temp folders (the spec's) and for the resume claims this run contradicted (mine, see below).
- `docs/user/troubleshooting.md`: three entries keyed on S11, S12 and S14; `landing/docs/troubleshooting.html` regenerated.
- Journal: a dated "Follow-up (2026-11-20): closing asks first" section; its tldr and one Decisions bullet updated; the `docs/building/_index.md` row updated.

## Spec problems and choices to review

1. **A type the spec's file list missed.** Rule 9 reads `setup_outcome`, which the server sends but `LocalStatusResponse` did not declare. I added one type-only line to `ui/src/api/types.ts` (not in target.md's in-scope list; no runtime change).
2. **S14's cause is a guess in one case.** S14 also shows when the start request got no answer at all and the server then reports no outcome (T4_notRunning). On localhost that usually means anyscribe was not running, so "because anyscribe was closed" is likely, but a start that timed out on a live server would land there too.
3. **T5 changed meaning, by design.** With adoption, "the wizard's read says running, the step's says not running" is now an adopted setup that ended. The step shows how it ended (here S14, since the fake "running" had no outcome behind it). In real use that pair of reads means the setup really ended in between, so the message is true.
4. **The resume claims elsewhere are wrong today.** The model card's "incomplete: the download resumes" (`LocalModelPicker.tsx`, showed on the Whisper Base card in `real-s14-after-restart-1440.png`) and troubleshooting's "A model shows as incomplete … the download picks up where it stopped" did not hold in this run. Both are outside this PR; logged in BACKLOG wave 2.
5. **Commit grouping.** Rules 1 to 11 live in the same component and were built together, so they are one commit (with the bundle); the records and this proof are separate commits. Mutations were run against that commit and restored with `git checkout`; the restored build gave the same bundle name, `index-CBp6eUC1.js`.

## What I could not prove

- A real Mac or Windows run, screen readers, and whether a reopened desktop app comes back on the same port (S12's "open it again: this page then shows…" assumes it does).
- Resume on the plain HTTP path (`HF_HUB_DISABLE_XET=1`): traced in the library code, not run.
- The `autoFocus` scroll fix was seen working once at 390 px; it was not mutation-tested (not one of the required guards).
- The harness cases fake the running state on top of real status answers; only the rule 12 walk used a real download, real stop and real restart.

## Checks (run before the last commit)

```
$ .venv/bin/ruff check src tests scripts
All checks passed!
$ .venv/bin/python -m pytest -q
931 passed, 6 skipped, 134 warnings in 60.40s (0:01:00)
$ cd ui && npm run lint && npm run build
> eslint .            (no findings)
../src/anyscribe/web/static/assets/index-BufnjB4u.css   36.47 kB
../src/anyscribe/web/static/assets/index-CBp6eUC1.js   396.30 kB   (same as committed)
$ python3 scripts/build-docs.py && python3 scripts/check-docs.py
rendered 6 pages + index → landing/docs        (check-docs exit 0, no diff after rebuild)
$ git grep -n "onRunning(" -- ':!docs/reviews'
ui/src/components/OnboardingWizard.tsx:734:    const report = (w: boolean) => onRunning(w);
$ git diff 96b76bc --stat -- src/anyscribe ':!src/anyscribe/web/static' install.sh install.ps1 landing/index.html tests .github pyproject.toml
(empty)
```

## Cleanup

- Stopped by pid after reading each command line: the resume server (8492), `slowproxy.py` (8499), `diskwatch.sh`; the harness server (8491) and `serve.py` (8497) after the final run; closed my preview tab.
- Uninstalled the 9 engine packages with `uv pip uninstall`; `uv pip freeze` matches the list taken before, and `uv pip check` reports all compatible. uv's own download cache (`~/.cache/uv`, shared) was left alone.
- Deleted the throwaway home with the Base model (142 MB). The harness home (`home-a`), instruments, logs and screenshots stay under `~/.review-runs/2026-11-20-onboarding-wave1-lock/`.

## Round 1 fixes (one entry per finding)

Fixer: Claude Opus 5.5 (Agent tool). Branch `feat/onboarding-wave1-lock`, base `ffdb7cc` (checked with `git rev-parse HEAD` before editing). The fix plan (`fix-plan-r1.md`) set every wording below; L1 was kept as residue (BACKLOG only).

Instruments (outside the repo, not committed): the round 0 harness in `~/.review-runs/2026-11-20-onboarding-wave1-lock/instruments/`, with S14's fixed strings updated, two new cases (`L3`, `LF3`), three new mutants in `mutate.py` (`M3`, `M3L`, `MLF3`), and one harness fix: `fresh()` now retries Skip for now up to three times, because a status read that ends watching in the 150 ms between Skip and Close setup hides S11 and left the dialog open (it failed T3's setup once in the first full run, `results/r1fix-all.json`, before T3's own checks ran; the round 0 copies are kept as `harness.r0.js`, `cases.r0.js`, `mutate.r0.py`). Server: `HOME=~/.review-runs/2026-11-20-onboarding-wave1-lock/home-r1fix .venv/bin/python -m anyscribe ui --port 8491 --no-open --local-only` (a new empty home), my own T3 preview tab, `serve.py` on 8497.

**Full harness, committed bundle `index-DyrxykgW.js`: 26 of 26 cases pass** (`results/r1fix-final-all.json`): T1, T1_500, T2, T3, T4, T4_notRunning, T4_refused, T5, T5_late, T6, T7, T8, T9, T10, T11, T12, T12b, F4, F1, T13, TG, T4v2, R3C1, R3C2 (round 0's 24) plus L3 and LF3.

**LF1, the resume claims. FIXED** (`261a1eb`).
- Changed: `LocalModelPicker.tsx` "incomplete: the download resumes" → "incomplete: setup downloads it again"; troubleshooting's incomplete entry "the download picks up where it stopped." → "the download starts again.". The fix plan's grep (`git grep -n -i "resume\|picks up where" -- ui/src docs/user src/anyscribe/skill CHANGELOG.md`) found four more claims that a stopped model download resumes, fixed the same way: Settings' button "Incomplete: resume download" → "Incomplete: download again" (`SettingsPage.tsx`; troubleshooting names that button, so both changed together), `configuration.md` "`anyscribe model pull <id>` resumes it." → "downloads it again.", the skill's `references/commands.md` "resume with `anyscribe model pull <id>`" → "download it again with …", and the `types.ts` comment. These four files are outside target.md's list; the fix plan's grep scope named their folders. The wave 2 BACKLOG line about the two strings is gone; a new wave 2 line keeps what is left outside this PR's scope: `anyscribe model info` prints "Resume the download: anyscribe model pull <id>" (`cli/models_cmd.py:415`, server-side code) and code comments in `providers/local_models.py` and `web/routes/models.py` say the same. The journal's bullet says what changed.
- Evidence the new wording holds: huggingface_hub 2.4.0 in `.venv`, `file_download.py` `_download_to_tmp_and_move` writes every download, xet or plain HTTP (`http_get` is called with no resume size), to a new `<name>.<uuid8>.incomplete` opened `"wb"`, so no process continues another's file; round 0's real run showed it (35.6%, then 0.6%). pyproject's floor is `huggingface-hub>=0.21`; an older hub could resume, which only makes "downloads it again" pessimistic.
- Siblings: the grep above, run last, has seven hits, none a model-download claim: batch `--resume` (`commands.md:383`, skill `commands.md:94, 199, 230`), chunk checkpoints of a long transcription (`configuration.md:27, 477`), and `OnboardingWizard.tsx:81`, the LF5 comment saying Try again does not resume. Bundle: "incomplete: setup downloads it again" 1 hit, "Incomplete: download again" 1, "the download resumes" 0, "resume download" 0. `landing/docs/configuration.html` and `troubleshooting.html` regenerated; check-docs exit 0.

**L2, S14 names no cause. FIXED** (`480e7c6`).
- Changed: S14 is "Setup didn't finish. Click Try again to start it again."; the code comment on its condition no longer says anyscribe restarted. Troubleshooting's entry is headed "Setup didn't finish." and reads "anyscribe isn't reporting a running setup or its result. This can happen after anyscribe was closed or restarted, or if the start request never reached it. Click **Try again** to start it again." (plus the existing line that choices are kept while the wizard stays open); the S12 entry's pointer to it uses the new heading. CHANGELOG: "if anyscribe then reports no setup and no result (after a restart, for example), it says "Setup didn't finish", with **Try again**." The journal quote is the new S14, with why it names no cause. Harness: `S14` in `harness.js` and `S14_FULL` in `cases.js` updated.
- Seen: T4_notRunning (the start got no answer, the real server reports no setup: the reviewer's exact path) passes with `redAlerts: ["Setup didn't finish. Click Try again to start it again."]`, `aboveButtons`, button "Try again"; T5 and T12 pass with the same sentence; T12b still shows the missing-part sentence when the outcome is `set_up`. At 1440 px: `screens/r1fix-s14-1440.png`.
- Siblings: `git grep "stopped before it finished\|because anyscribe was closed"` outside `docs/reviews`, `landing/docs` and the bundle: one hit, `troubleshooting.md:87`, about Homebrew (unrelated). Bundle: new S14 1 hit, "because anyscribe was closed" 0.

**L3, a failed setup shows no server text. FIXED** (`54e2794`).
- Changed: on the ending read with `setup_error`, the step sets the one red line to "anyscribe couldn't finish setting up local transcription. Click Try again." (it reuses the existing `missing` block, so the button reads "Try again" and the block sits just above the buttons); the separate raw `setupError` block and its state are deleted, and the install log no longer opens by itself. The server already writes the raw text to the install log as `[error] …` before it reports the setup stopped (`web/routes/local.py`), so it stays reachable through "show install log". CHANGELOG's W6 entry says so in one sentence.
- New case `L3`: the setup runs, its log answers `[error] HTTP 503: {"detail":"upstream timeout","status_code":503}`, then the status says stopped with `setup_error` = that text and outcome `failed`. Guarded, all six checks pass: the red line is exactly the plain sentence, above the buttons, button "Try again", not watched; the dialog's whole visible text has no `503`, `status_code`, `"detail"`, `upstream timeout` or `{"`; no `<pre>` and the control reads "show install log (2 lines)"; clicked by hand, the log shows the raw `[error]` line; with it open, the text outside the log still has none of them; Escape closes at once, flag unset. At 1440 px: `screens/r1fix-setup-failed-1440.png`.
- Mutant M3 (`setMissing(s.setup_error ?? SETUP_FAILED)`, the server's text in place of the sentence): **L3 fails**: `redAlerts: ["HTTP 503: {\"detail\":\"upstream timeout\",\"status_code\":503}"]`, and the on-screen leak list is `["503","{\"","upstream timeout","status_code","503"]` (`results/M3.json`).
- Mutant M3L (the sentence kept, `setLogOpen(true)` added back): **L3 fails**: the control reads "hide install log (2 lines)", a `<pre>` is on screen, and the visible text leaks the same five matches (`results/M3L.json`).
- Restored: `git checkout`, rebuild gives `index-DyrxykgW.js` again, L3 passes in the final run. T11 (an old `setup_error` from a read sent before Download) still passes: nothing old shows.

**LF2, S12 for someone who closed anyscribe. FIXED** (`4735e9c`).
- Changed: S12 is "Can't reach anyscribe right now. If you closed it, the download stopped too: open anyscribe again and this page shows a Try again button to start it again." Troubleshooting's S12 entry now has a bullet for each reader: closed anyscribe ("the download stopped too", reopen, then "Setup didn't finish" with **Try again**) and anyscribe still open (the message clears by itself and the page shows the download or how it ended). CHANGELOG and the journal quote only S12's first sentence, which did not change.
- Seen: T6, T7, T9, T13 and R3C1 pass (`s12` true where expected; the harness matches S12's first sentence). At 1440 px, with the reads failing: `screens/r1fix-s12-1440.png`, the new sentence in the amber notice.
- Siblings: "if it is still running" now appears only in troubleshooting's S11 entry (`troubleshooting.md:576`), where it is right: closing the wizard does not stop anyscribe. Bundle: new S12 1 hit, the old "if it is still running, or a Try" 0.

**LF3, Escape on the open confirmation. FIXED** (`f1e20f7`).
- Changed: the Modal's close callback is `confirmClose ? setConfirmClose(false) : askOrClose(false)`. Escape and a click outside share that callback in `Modal.tsx`, so a click outside the open confirmation also hides it; Skip for now with it open leaves it open. Rule 3 above now records the change.
- New case `LF3`, guarded, six checks pass: first Escape asks (S11, focus on Keep setting up); a second Escape hides S11 with the wizard open, still watched, flag unset; a click outside asks, a second hides it; two Skip clicks leave S11 open and the wizard open; Close setup closes with the flag unset. With the real Escape key in my tab (preview `press`): first press, S11 with focus on Keep setting up; second press, S11 gone, wizard open, "Setting up… [disabled]", flag `null`.
- Mutant MLF3 (the round 0 callback, `onClose={() => askOrClose(false)}`; its build is byte-identical to the LF2 commit's `index-BlFO7EtI.js`): **LF3 fails** at "Escape on the open confirmation hides it" with `"s11":true,"focus":"Keep setting up"` after the second Escape, nothing visible changed; the click-outside check fails the same way (`results/MLF3.json`). Restored: LF3 passes.

**LF4, CHANGELOG. FIXED** (`e28e143`): "the wizard is never locked; Back and the model choices are off until the setup finishes." `git grep "only Back is off"` outside `docs/reviews`: none.

**LF5, the code comment. FIXED** (`a65b6d8`): "Try again does not resume a half-downloaded model: a real download stopped at 35.6% restarted from 0% (docs/reviews/2026-11-20-onboarding-wave1-lock/proof.md, rule 12)." Comment only; the rebuilt bundle kept the same name.

**L1, residue. NOT FIXED, by the fix plan; BACKLOG line added** (`2cfb7b9`), wave 2, the fix plan's wording verbatim.

### Strings in the committed bundle `index-DyrxykgW.js`

New S12, S14, the setup-failure sentence, "incomplete: setup downloads it again" and "Incomplete: download again": one hit each. "because anyscribe was closed", "if it is still running, or a Try", "the download resumes", "resume download": none.

### Checks (run before this commit)

```
$ .venv/bin/ruff check src tests scripts
All checks passed!
$ .venv/bin/python -m pytest -q
931 passed, 6 skipped, 134 warnings in 67.05s (0:01:07)
$ cd ui && npm run lint && npm run build
> eslint .            (no findings)
../src/anyscribe/web/static/assets/index-BufnjB4u.css   36.47 kB
../src/anyscribe/web/static/assets/index-DyrxykgW.js   395.95 kB   (same as committed)
$ python3 scripts/build-docs.py && python3 scripts/check-docs.py
rendered 6 pages + index → landing/docs        (check-docs exit 0, no diff after rebuild)
$ git grep -n -i "resume\|picks up where" -- ui/src docs/user src/anyscribe/skill CHANGELOG.md
7 hits, each explained under LF1 (batch --resume, chunk checkpoints, the LF5 comment)
$ git status
clean before this file's edit
```

### What I could not prove

- L3's raw text reaching the log was faked in the harness (a set log answer); the server side, that `_background_setup` appends `[error] <text>` before it sets `running` false, is read from `web/routes/local.py`, not run with a real failing download.
- "starts again" holds for huggingface_hub 2.4.0, what a fresh install gets; not checked against older hubs the `>=0.21` floor allows.
- Everything round 0 listed (real Mac or Windows, screen readers, the desktop app's port after a reopen).

### Cleanup

- Stopped by pid after reading each command line: the dashboard (8491, pid 1606393) and `serve.py` (8497, pid 1606395); no listener left on 8490 to 8499. Closed my preview tab.
- Kept under `~/.review-runs/2026-11-20-onboarding-wave1-lock/`: `home-r1fix`, the instruments and results, `screens/r1fix-*.png`.

## Lead-made changes after the round 2 re-check (post-cap, reported to the owner as unreviewed)

- **R2LF1** `OnboardingWizard.tsx`: the setup-failure sentence is now "anyscribe couldn't finish setting up local transcription. Click Try again; if it fails again, <untick local transcription and go on | choose a cloud service instead>." (the step's existing `otherwise(required)` helper, as its three sibling sentences use).
- **R2LF2** `OnboardingWizard.tsx`: while anyscribe can't be reached, the progress line reads "Waiting for anyscribe…" instead of claiming the download is running.
- **R2LF3** `docs/user/troubleshooting.md`: an entry keyed on "anyscribe couldn't finish setting up local transcription." (landing/docs regenerated).
- **R2LF4** `src/anyscribe/cli/models_cmd.py`: `anyscribe model info` says "Download it again: anyscribe model pull <id>" instead of "Resume the download"; BACKLOG's line now covers only the code comments.
- BACKLOG: L1 marked "Before the next PyPI release"; R2L1 added to wave 2.

Proof (harness copies in `~/.review-runs/2026-11-20-onboarding-wave1-lock/instruments/`, results in `results/`):
- New lead check `lead-r2.js` on the OLD build (`index-DyrxykgW.js`, 03f6562): FAIL "failure sentence names a way out" (got "...Click Try again."), FAIL "progress line says Waiting for anyscribe" (got "Installing the local engines and downloading the model…"); `results/lead-r2-oldbuild.json`.
- Same check on the NEW build (`index-BKmerAkr.js`): all 4 PASS; `results/lead-r2-newbuild.json`.
- Full suite on the new build (`results/lead-postcap-all.json`): 25 of 26; T7 failed only because the harness's progress reader recognised just "Downloading|Installing|Install log". With the reader taught "Waiting for anyscribe" and T7's and L3's expected strings updated (old copies kept as `harness.r1.js`, `cases.r1.js`), T7, T6 and T9 re-run PASS (`results/lead-t7.json`).
- `ruff check src tests scripts`: All checks passed. `pytest -q`: 931 passed, 6 skipped. `npm run lint && npm run build`: clean, bundle `index-BKmerAkr.js`. `build-docs.py` + `check-docs.py`: exit 0.
