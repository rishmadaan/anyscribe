Copied from the review run folder; absolute home-folder paths rewritten as ~ paths and the lead's scratch path masked; the byte-exact original stays in ~/.review-runs/2026-11-19-local-first-parakeet/.

~~~~~
FIT REVIEW, round 2. Target: feat/local-first-parakeet @ 8c5d10d, diff b2bafa7..8c5d10d. Read-only. I wrote no files and ran no tests, builds or servers.

## 1. Verdict

**CONDITIONAL on R2F1 and R2F2.** Both are small copy or behaviour changes, not rework.

The round-1 fit problems are fixed or mostly fixed. The headline one is gone: a key-free user no longer sees an API-key warning after the wizard. The fixer proved it with a browser walk, including a failing run with the fix removed, and I traced the code (App.tsx key bump, TranscribePage `qualityPicked`).

Help me choose now explains why in plain words. English gets "as accurate as Turbo on English, about 4 times faster on our test desktop". Hindi gets "most accurate on Hindi in our test" plus the reason to set the language. "Something else" has its own sentence. It also states the download sizes and shows what it selected. The screens match the approved mockup closely, and they now carry the benchmark caption.

Two things remain that the owner would object to:
- **R2F1:** in Settings, clicking an answer to the language question now switches an existing user's default model or starts a download of up to 2.3 GB.
- **R2F2:** the Hindi advice tells every "Indian language" user to set their language to Hindi, which is wrong for a Tamil or Bengali speaker.

## 2. Round-1 F findings: status

| Id | Status | Evidence |
|---|---|---|
| F1 stale quality / API-key warning | FIXED | Traced `ui/src/App.tsx` (TranscribePage `key={configVersion}`, bumped on wizard close) and `TranscribePage.tsx` (quality sent only when picked; submit blocked until config loads). Proof shows the mutant reproducing the WARNING and the fix removing it. |
| F2 pre-select | FIXED in wizard and setup modal; over-applied in Settings | `fx-wizard-2-mix-1440.png` shows Parakeet checked right after answering, with no "Use this" button. In Settings the same change now commits a model change or a download. See R2F1. |
| F3 hidden second download | FIXED | The suggestion ends with "Downloads 670 MB + 1.6 GB, plus the 75 MB language check." The button names both models and 2.3 GB. All set and the modal list Turbo with live status. Leftover nit R2F5. |
| F4 mid-recording switches | FIXED | Three-window check. The wording "start, middle and end of each recording" is used in CHANGELOG, picker, recommendation and docs; "never writes gibberish" is gone. The mix advice adds the Hinglish sentence. Proof shows a real 35 s English plus Hindi clip routed to Turbo. |
| F5 reasons explain why | FIXED, with one new gap | "Something else" has its own branch. The English sentence is clear. Memory is cited only when it changed the pick. "Set my language to Hindi" exists on the Web (a button) and in the CLI (yes/no). The switch note ends "To skip the check, set your language to <Language> in Settings." New gap: R2F2. |
| F6 card numbers unqualified | FIXED on screens; docs leftover | Caption under the cards in Settings, the wizard, the modal and the CLI. "on our test desktop" in the reasons and the first-run line. The docs still say "typical": R2F4. |
| F7 first-run line missing | FIXED | Visible in `fx-wizard-1-choice-1440.png`; now reads the static `/api/local/registry`. |
| F8 getting-started cloud-first | FIXED | "What you need" leads with "On this computer (recommended)". |
| F9 nits | PARTLY | Fixed: step labels ("Step 1", then "Step 2 of 3"), display names in All set, the result card and the CLI, one size per card, visible Reinstall/Delete labels, and a not-downloaded card saying "Downloading; becomes your default when done". Still left: Settings "Model parakeet-v3 · change it on the local card below" and the "What runs by default" rows show raw ids (the fixer named this himself). |
| F10 repo hygiene | PARTLY | Screenshots are out of the repo and target.md is masked. But see R2F6: two tracked files still hold the scratch path. `mockup.html` (tracked) still says "your desktop (i5-10600K)" and "ElevenLabs transcripts already in your vault". The lead left that as owner's call. |

## 3. New findings, most severe first

**R2F1. should-fix. CONFIRMED (code trace).** This touches must-never 3 ("an existing user's model changes without their choice").
- **Where:**
  - `ui/src/components/LocalModelPicker.tsx:305`: `if (r.primary) onUse(r); // answering applies the suggestion`
  - `ui/src/pages/SettingsPage.tsx:194-214`: `handleRecommendation`, then `chooseLocalModel`, then `handleSave({local_model})` or `handlePull`, then a pull of every `also` model.
- **Scenario (the lens's own job):** an existing Whisper Turbo user upgrades, opens Settings and clicks Help me choose. They click "A mix (e.g. English and Hindi)" just to see the advice.
  - With nothing else downloaded, Parakeet v3 (670 MB) and Whisper Tiny start downloading at once, and Parakeet is set to become the default when done.
  - If Parakeet is already on disk, the default flips immediately.
  - Clicking through the other answers to compare fires more downloads and moves the pending default each time.
- **Why it happens:** in the wizard and modal, "selected" means nothing until the big setup button. In Settings, selecting a card is the commit, so the round-1 F2 fix turned "pre-select" into "switch and download". The owner's market includes metered connections, and a surprise 2.3 GB download from a click labelled with a language is exactly what he would object to.
- **Fix (Settings only; keep the wizard and modal as they are):**
  - Answering highlights the suggested card(s) and adds a "Suggested" label.
  - Show one button that commits: "Use Parakeet v3 + Whisper Large v3 Turbo (downloads 2.3 GB)", or "Use Whisper Large v3 Turbo (already downloaded)".
  - Change the header from "Selected:" to "Suggested:" until that button is clicked.
- **Test:** in Settings, answer "English" with Parakeet not on disk. Assert `/api/config` `local_model` is unchanged and the pull queue is empty until the button is clicked.

**R2F2. should-fix. CONFIRMED (code).** The Hindi advice is given to every "Hindi or another Indian language" answer.
- **Where:**
  - `src/anyscribe/core/local_recommend.py:172-176`: the reason reads "Set your language to Hindi: Turbo is about 3 times more accurate…".
  - The same file sets `set_language: "hi"` for every `indian` answer.
  - `src/anyscribe/cli/onboard.py:272`: the CLI asks "Set your language to Hindi?".
  - The Web button "Set my language to Hindi" in `LocalModelPicker.tsx`.
- **Scenario 1:** a Tamil or Bengali speaker answers "Hindi or another Indian language". They are told, as an instruction, to set their language to Hindi. Following it forces Whisper to treat Tamil audio as Hindi.
- **Scenario 2:** a Hindi speaker who also has English recordings is not told that `language: hi` then applies to every file, English included, and switches off the language check.
- **Fix (copy only):**
  - Reason: "If your audio is Hindi, set your language to Hindi: Turbo is about 3 times more accurate on Hindi when it is told the language. Every recording is then treated as Hindi."
  - Button: "My audio is Hindi: set language to Hindi".
  - CLI: "Is most of your audio Hindi? Setting the language to Hindi makes Turbo about 3 times more accurate on it."

**R2F3. should-fix. CONFIRMED (code trace). Owner's call on scope.** A key-free person who skips onboarding still meets two API-key messages and no hint of the free option.
- **Where:**
  - `src/anyscribe/config/settings.py:38,41`: the defaults are `provider: openai`, `quality: balanced`.
  - `src/anyscribe/core/resolve.py:79-83`: produces the WARNING line.
  - `src/anyscribe/providers/openai.py:41-42`: "OPENAI_API_KEY not set. Run 'anyscribe onboard'…".
- **Scenario:**
  - Someone clicks "Skip for now" in the wizard, or runs `pip install anyscribe` and then `anyscribe transcribe <url>` without onboarding.
  - They get "WARNING: quality 'balanced' wants deepgram but no DEEPGRAM_API_KEY is set, using openai instead", then a failure about OPENAI_API_KEY.
  - `fx-settings-restart-banner-1440.png` shows the same WARNING in Settings' "Next run" box on a key-free throwaway HOME.
- **Where this sits:** not the local path, so must-never 1 holds as worded. But the owner's ask was "nobody has to worry about API keys", and the first thing this user reads is about two keys. The spec never addressed the un-configured default.
- **Fix:** smallest safe one: when no cloud key is set, add one line to that error and warning: "Or transcribe free on this computer, no key needed: `anyscribe local setup --model parakeet-v3` (or Settings, then local)." Changing the dataclass default would only affect people with no config file, since saved configs write every field. But it would also catch env-key users without a config, so I would not do that in this PR.

**R2F4. nit. CONFIRMED.** The docs still generalise one machine as "typical".
- **Where:**
  - `CHANGELOG.md:21` ("on a typical 6-core desktop")
  - `docs/user/getting-started.md:36` and `:108` ("a typical desktop")
  - `docs/user/providers.md:410`
  - `docs/user/troubleshooting.md:414`
- **Problem:** the screens now say "our test desktop … your computer may be faster or slower". The lead's own Mac does Parakeet at about 2.5 min per hour once the CPU fix is in.
- **Fix:** replace "a typical" with "our".

**R2F5. nit. CONFIRMED (code + screenshot).** The All set and modal "finished" text does not follow the status beside it.
- **Where:** `OnboardingWizard.tsx:882-886` and `LocalSetupModal.tsx:178-181`.
- **Problem:** `fx-wizard-4-allset-ready-1440.png` shows "✓ ready" next to "…works once it finishes downloading. You can start transcribing now; the download carries on." After a failure it still says the same.
- **Fix:** render that sentence only while the status is downloading or waiting. On failure, say "Hindi and other languages won't work until you download it in Settings."

**R2F6. nit. CONFIRMED.** Tracked files still carry the lead's scratch path, including the OS username.
- **Where:** `docs/reviews/2026-11-19-local-first-parakeet/findings.md` and `report-opus-r1.md`. Both quote "`<lead scratch folder>/...`" inside round-1 F10's own text; `git ls-files | xargs grep -l tmp/claude-1000` finds both.
- **Fix:** mask it the way target.md was masked, before the squash and first push.

**R2F7. nit. CONFIRMED (code).** The restart banner assumes a terminal.
- **Where:** `ui/src/components/LocalSetupNotes.tsx:18-22`, which says "in the terminal where `anyscribe ui` runs, press Ctrl+C".
- **Problem:** the one-line installer's default is desktop mode: a tray or launchd service started at login, with no terminal. The people most likely to hit this banner are existing users upgrading from v0.18.3 with PyAV 19, many of them in desktop mode.
- **Fix:** add "Using the app icon? Quit anyscribe from its menu-bar or tray icon, then open it again."

**R2F8. nit. CONFIRMED.** A key-free local user's Settings page leads with three amber "needs API key" markers in "What runs by default" (`fx-settings-2-pending-1440.png`, `fx-settings-3-hindi-1440.png`).
- **Why it matters:** this is informational, and it predates this PR. But it is the most prominent thing on the page for the exact user this build serves.
- **Fix:** when the active tier is local or custom-local, use muted wording: "add a key to use".

## 4. Answers to the brief

- **Is this the job he asked for, and the simplest instrument?** Yes.
  - It delivers the ask's three parts: keyless local by default, Spokenly-style cards, and guidance that explains why.
  - It is not gold-plated. The extra surfaces (restart banner, incomplete-download state) each answer a real failure that was found.
  - The one place it got less simple than intended is R2F1, where one rule was applied to three surfaces with different commit semantics.
- **Does "help me choose" explain why?** Mostly yes, now.
  - Every answer opens by citing what the person said and gives a concrete comparison: "as accurate as Turbo on English, about 4 times faster on our test desktop"; "most accurate on Hindi in our test". It ends with sizes.
  - The mix answer explains what happens (two models, the check, the Hinglish caveat). It does not say why Parakeet is the main model rather than Turbo. One clause would do it: "Parakeet is the main one because it is about 4 times faster on English."
  - The only wrong "why" is R2F2.
- **Card numbers (lead evidence 3):** now qualified on every screen by the caption. Only the docs over-claim (R2F4).
- **Lead evidence 2 (the WARNING):** resolved for the wizard path (F1). It is still reachable for a key-free user who skipped onboarding (R2F3).

## 5. Pending owner checks

- **The Mac re-measure.** Fix plan item 3 says the lead would re-measure with the CPU provider forced. proof.md says "Mac timing not re-measured here (lead does it)", and I saw no Mac numbers after the fix. Until that run, "about 10 min per hour" and "4 times faster" are unverified on his own machine.
- **R2F3 scope:** should a key-free person who skips the wizard get a pointer to local setup in this PR?
- **R2F1 behaviour:** in Settings, should answering only suggest (my recommendation), or switch?
- **F10 leftovers:** does `mockup.html` with "your vault" and "i5-10600K" stay in the public repo?

## 6. What I could not check, and what I inspected

**Could not check:**
- No browser walk. To settle R2F1: run `anyscribe ui --port <spare> --no-open --local-only` on a throwaway HOME with only Turbo cached. Open Settings, click Help me choose, click "English", then `GET /api/config` (local_model) and `GET /api/local/status` (queue).
- The 390 px wizard screenshots are full-page captures of a fixed modal over Settings, so I could not judge the wizard's own scroll at 390 px from them.
- I did not drive the interactive CLI onboarding; I read the new strings in the diff of `src/anyscribe/cli/onboard.py`.

**Inspected:**
- **Brief and packet:** brief-r2-fit.md, ask.md, spec.md, target.md, lens.md, declined.md, findings.md (my round-1 report), review-log.md, fix-plan-r1.md, proof.md (the round-1 fixes section) and mockup.html (text).
- **Screenshots:** every fx-*.png (wizard 1-4 at 1440, Hindi wizard and All set at 390, Settings partial/pending/Hindi/390/restart banner, modal finished, both result cards).
- **Code:**
  - `core/local_recommend.py` (all)
  - `LocalModelPicker.tsx` (cards, explainer, HelpMeChoose)
  - `SettingsPage.tsx` (choose and recommendation handlers)
  - `OnboardingWizard.tsx` (All set)
  - `LocalSetupModal.tsx`, `LocalSetupNotes.tsx`
  - App/TranscribePage diff
  - `core/resolve.py`, `config/settings.py`, `providers/local.py` (load and error paths)
  - `mcp/server.py` (doctor, set_config)
  - `core/config_set.py`, `web/routes/system.py`
- **Docs and grep:** CHANGELOG Unreleased, README diff, getting-started, skill SKILL.md lines; a grep of the diff for owner data.

Skipped: engine and guard internals, install paths and test validity (the correctness reviewer's lane). Advice outside this PR's scope: MCP has no tool to install engines or download a model. On main it had none either, so an MCP-only agent can recommend but not set up local transcription. Worth a backlog line.
~~~~~
