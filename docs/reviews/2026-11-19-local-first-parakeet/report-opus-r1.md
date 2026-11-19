Copied from the review run folder; absolute home-folder paths rewritten as ~ paths and the lead's scratch path masked; the byte-exact original stays in ~/.review-runs/2026-11-19-local-first-parakeet/.

~~~~~
FIT REVIEW, round 1. Target: feat/local-first-parakeet @ 87dbd2f (code 0aff252), diff b2bafa7..87dbd2f

## 1. Verdict

**NOT YET.** This is the job the owner asked for, and the spec mostly fits it. The Parakeet engine, the language check, the "On this computer vs cloud" first choice, the cards and Help me choose are all there, and the Settings card follows the approved mockup closely. One problem breaks a must-never rule. A brand-new key-free user who finishes the new wizard and transcribes straight away is shown "WARNING: quality 'balanced' wants deepgram but no DEEPGRAM_API_KEY is set" (F1). This is not a rare race: it happens every time on the main new-user path. After F1, the Help me choose guidance has gaps. It does not always explain *why*, it does not apply its own suggestion until a second click, and it hides a 1.6 GB extra download (F2 to F6).

## 2. Findings (most severe first)

**F1. blocker. CONFIRMED by trace (not run in a browser).** `ui/src/pages/TranscribePage.tsx:48` and `:56-67`, `ui/src/App.tsx:47-52`.
- **Scenario:** fresh install, no keys. `anyscribe ui` opens. The Transcribe page mounts behind the wizard and fetches `/api/config` once (`useEffect(..., [])`). No config has been saved yet, so it gets the dataclass default `quality: "balanced"` (`config/settings.py:41`). The user picks On this computer, sets up Parakeet and clicks "Finish & start transcribing". `onClose` only hides the modal. The Transcribe page is not remounted and does not refetch, so its `quality` state is still "balanced".
- **Result:** the first paste-and-transcribe sends `quality: "balanced"`. `web/routes/transcribe.py:74-75` applies it, and `core/resolve.py:79-83` emits the deepgram-key WARNING on the local path. The options summary under the URL box also reads "balanced", even though onboarding saved `custom`.
- **Lead question 2:** this is exactly the builder's `result-note-1440.png`. It is deterministic on the wizard path, not a load-time race.
- **Fix:** send `quality` only when the user actually changed it, so the server uses the saved config. Also refetch config when the wizard closes (for example, App bumps a key on TranscribePage, or the wizard calls a refresh callback).
- **Test that settles it:** walk wizard, then Finish, then transcribe in one page session, and assert the job's `plan.notes` carry no "WARNING".

**F2. should-fix. CONFIRMED (code).** `ui/src/components/LocalModelPicker.tsx:286` (`ask`) and `:356` (`onUse` only on the button).
- **Problem:** answering the language question does not select the suggestion. Only a second click on "Use this" does. The spec says "Defaults pre-select the recommendation".
- **Scenario:** in the wizard a Hindi speaker clicks "Hindi or another Indian language" and sees "Suggested: Whisper Large v3 Turbo". Parakeet stays selected, and the big button still says "Download Parakeet v3 and set up" (`OnboardingWizard.tsx:689`). They click it. Their first Hindi transcript then fails with "download Turbo".
- The same gap applies to "A mix": without "Use this", Turbo is never queued.
- **Fix:** apply the suggestion when the question is answered, and drop the "Use this" / "Selected" button. The "Selected" label also looks like a primary call to action that does nothing.

**F3. should-fix. CONFIRMED (code).** Mix path: Turbo downloads without the user being told. See `OnboardingWizard.tsx:540-545` (pulls `rec.also` after setup), `cli/onboard.py:334`, and the Settings `handleRecommendation`.
- **Problem:** the user is told "Download Parakeet v3 and set up" (670 MB). Another 1.6 GB of Turbo then downloads in the background.
- Neither the recommendation box, the button, the "All set" summary (`OnboardingWizard.tsx:791-796`, which lists only parakeet-v3) nor the CLI line ("Downloading Whisper Large v3 Turbo for the other language…", no size) states the size or that it is still running.
- **Second effect:** if the user transcribes Hindi while that download is still running, the guard can pick the half-downloaded Turbo. The builder's own risk note says "cached" means any bytes on disk. That fails loudly, but confusingly.
- **Fix:**
  - Put the total in the suggestion, e.g. "downloads 670 MB + 1.6 GB".
  - Put it on the button: "Download Parakeet v3 + Whisper Large v3 Turbo (2.3 GB)".
  - Show Turbo's download progress on All set.
  - Make the CLI title say "Parakeet v3 + Whisper Large v3 Turbo", with sizes.

**F4. should-fix. PLAUSIBLE (spec-level, not reproduced).** The "A mix (e.g. English and Hindi)" answer, `core/local_recommend.py:168-174`, plus the CHANGELOG line "anyscribe never writes Parakeet gibberish" (`CHANGELOG.md:23`).
- **Problem:** the language check listens only to the first 30 seconds of each file. Someone who picks "a mix of English and Hindi" most likely has recordings that switch language mid-file (Hinglish). That is the owner's own market.
- **Scenario:** a voice note opens in English for 30 seconds, then goes to Hindi. It passes the check, and Parakeet writes the Hindi part as romanized gibberish with no note. That is the must-never, at the level of parts of a file.
- The reason text "anyscribe switches to Turbo automatically for Hindi" promises more than this, and "never writes gibberish" in the CHANGELOG over-claims.
- **Fix, owner's call:**
  - (a) For "mix", make Turbo the main model. It is equally accurate on English in the spec's own table; it is just slower.
  - (b) Or keep Parakeet, and say plainly: "Each recording is checked by its first 30 seconds; if one recording switches between English and Hindi, Turbo is the safer pick."
  - Either way, reword the CHANGELOG to "checks the language of the first 30 seconds".
- **How to settle:** one code-switched clip through `anyscribe transcribe` with parakeet-v3 as the default.

**F5. should-fix. CONFIRMED (code).** The Help me choose reasons do not always explain *why*. See `local_recommend.py:147-185`.
- **"Something else" cites Hindi.** "Indian" and "other" share one branch. A Japanese speaker reads "You said a language outside English and Europe… Turbo fits: it was the most accurate local model on Hindi in our test."
- **The English reason is confusing:**
  - "Parakeet v3 fits: it matches the most accurate local model on English at about 4× its speed." A reader cannot tell what "it" and "its" refer to. Parakeet is itself the top-rated model.
  - It cites "15.5 GB of memory", which plays no part in that pick, so it reads like reasoning without being reasoning.
- **The Hindi pick leaves language on auto.** The spec's own numbers show Turbo on auto-detect is about 3× worse on Hindi (character error rate 28.5) than with language set to Hindi (9.9). Nothing tells the user to set it, or offers to. The mockup's note had "set your language to Hindi in Settings"; the built note dropped it.
- **Fix:**
  - Give "other" its own sentence, about 95+ languages.
  - English: "As accurate as Whisper Large v3 Turbo on English, and about 4 times faster on a typical desktop."
  - Cite memory only when it changed the pick.
  - For the Hindi answer, add one line plus a one-click "Set my language to Hindi", and restore the mockup's next step on the switch note.

**F6. should-fix. CONFIRMED (code + screenshots).** The speed numbers on the web cards claim more than anyone knows. See `LocalModelPicker.tsx:176`, the `use_for` text, and `local_recommend.py` "4×".
- **Problem:** "1 hour of audio ≈ 10 min", "Fastest accurate option" and "about 4×" are shown with no note on which machine they were measured.
  - The approved mockup had that footnote.
  - The CLI table has a caption (`cli/models_cmd.py:123`).
  - The web picker has neither.
- **On the owner's Mac (lead evidence 1),** with the shipped default runtime settings:
  - Parakeet loads in 110 s and runs at 3.1× realtime.
  - Turbo runs at 3.2×.
  - So "Fastest" and "4× faster" are false there.
  - With the CPU fix they become understated: 23.6× against 3.2×.
- **Lead question 3:** yes, the screen claims more than it knows.
- **Fix:** add one caption line under the cards: "Times measured on a 6-core desktop without a graphics card; your computer may differ." This depends on the correctness side forcing `CPUExecutionProvider`; without that fix, the Mac claim is wrong even with the caption.

**F7. should-fix. PLAUSIBLE.** `OnboardingWizard.tsx:315-321`.
- **Problem:** the approved first-run line "Downloads Parakeet v3 (670 MB) once. About 10 minutes per hour of audio…" is missing from all three wizard-1 screenshots (390, 1000, 1440). It renders only after `/api/local/status` resolves, so either the screenshots were taken early or the call failed on a fresh home.
- **Settle:** open the wizard on a fresh HOME, wait 3 s, look again.
- **Fix if it is slow:** show the size from a static fallback, or show a loading state.

**F8. should-fix. CONFIRMED.** `docs/user/getting-started.md:36-37` ("What you need") still says the local provider "runs Whisper on your machine" and "Or an API key… OpenAI is the default". That contradicts the local-first story told 70 lines later. Fix: lead with local (Parakeet), cloud second.

**F9. nit. CONFIRMED (screenshots).** Smaller issues:
- **Step numbering:** the local path jumps from "Step 1 of 5" to "Step 3 of 5" because the API-key step is skipped.
- **Raw IDs instead of names:**
  - The "All set" summary shows raw IDs ("Provider local", "Local model parakeet-v3").
  - So does the result card ("local · large-v3-turbo").
  - So does the CLI's final "Default model: parakeet-v3" (`cli/onboard.py:343`).
  - The rest of the UI uses display names.
- **Two sizes on one card:** "downloaded · 639 MB" sits beside "Download 670 MB", and 1547 MB beside 1.6 GB.
- **Clicking a not-downloaded card in Settings does nothing and says nothing.** It is aria-disabled with no visible reason. Add "Download it first to make it the default".
- **Icons with no visible label:** the reinstall and delete icons have no visible text (aria-label only).

**F10. nit. CONFIRMED.** Repo hygiene on the public repo:
- The packet adds about 7 MB of PNGs, the first screenshots ever committed under `docs/reviews`.
- `target.md` carries `<lead scratch folder>/...` paths. `/Users/rish` paths already exist in earlier packets on main, so this has precedent.
- `mockup.html` says "measured on your desktop (i5-10600K)" and "scored against the ElevenLabs transcripts already in your vault".
- None of this is transcript text. Owner's call whether the screenshots and mockup belong in the public repo or should stay in the review-runs folder.

## 3. Answers to the brief's questions

- **Q2 (where the WARNING came from):** see F1. It comes from TranscribePage's stale "balanced" state, captured before the wizard saved `quality: custom`. A real key-free user reaches it every time on the wizard, then Finish, then transcribe path. CLI and headless onboarding set `custom` and do not hit it.
- **Q3 (card numbers):** see F6. They come from one Linux desktop, and the web UI does not say so. On the Mac they are wrong in both directions, depending on the CoreML/CPU fix.
- **Is this what he asked for / is it the simplest thing?** Yes on scope. The Spokenly-style cards and Help me choose match the ask and the mockup. The Settings card is a faithful build of mockup panel 1. Not gold-plated: the "beyond spec" items are small and useful. The one place it is not simplest is the extra "Use this" click (F2). The 5-step wizard, including the workspace step, is pre-existing; it is heavier than the mockup's one-screen first run, but acceptable.

## 4. Pending owner checks

- For "A mix", should the main model be Turbo (safe for Hinglish recordings) or Parakeet with a plain warning (F4)?
- Is a 1.6 GB background download acceptable on the mix path, provided it is shown up front (F3)?
- On his Mac, after the CPU-runtime fix: does the first Parakeet run feel fast, and does the "4× faster" sentence hold?
- Do the screenshots and the mockup belong in the public repo (F10)?

## 5. Could not check, and what I inspected

- I ran no browser, server or tests, per the brief.
- F1 is traced, not reproduced. To settle it: fresh `HOME`/`HF_HOME`, `anyscribe ui --port <spare> --no-open --local-only`, then wizard, then On this computer, set up, Finish, then submit a local file, then `GET /api/jobs/<id>` and check `plan.notes` for "WARNING".
- F4 needs a code-switched English-then-Hindi clip: `anyscribe transcribe <clip> --json` with `local_model: parakeet-v3`.
- F7 needs the wizard opened and given time to load.
- I did not drive the interactive `anyscribe onboard` TUI; I read it in `cli/onboard.py`.
- **Inspected:**
  - The packet: ask, spec, target, proof, lens, mockup.html, all 14 screenshots.
  - UI files: `OnboardingWizard.tsx`, `LocalModelPicker.tsx`, `SettingsPage.tsx` (diff), `TranscribePage.tsx`, `App.tsx`, `ResultCard.tsx` (diff).
  - Backend files: `core/local_recommend.py`, `core/resolve.py`, `config/settings.py`, `web/routes/local.py`, `web/routes/transcribe.py`, `cli/onboard.py` (diff), `cli/models_cmd.py`, `cli/main.py` doctor, `providers/local_models.py` (copy fields).
  - Docs: CHANGELOG Unreleased, README and getting-started diffs, greps over docs and skill for "4×" claims.

Skipped: correctness of the engine, the guard internals and the install paths. Those belong to the correctness reviewer. Biggest risk: F1 shows an API-key warning to exactly the user this build is for.
~~~~~
