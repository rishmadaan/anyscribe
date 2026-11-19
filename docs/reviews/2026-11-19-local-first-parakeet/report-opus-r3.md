Copied from the review run folder; absolute home-folder paths rewritten as ~ paths; the byte-exact original stays in ~/.review-runs/2026-11-19-local-first-parakeet/.

~~~~~
FIT REVIEW, round 3 (final). Target: feat/local-first-parakeet @ 5551230, diff b2bafa7..5551230. Read-only. I wrote no files and ran no tests, builds or servers.

## 1. Verdict

**CONDITIONAL on R3F1**, a copy and text-display fix of a few lines.

Every round-2 fit finding is fixed except R2F3, which is only partly fixed. Settings and the wizard now read right against the approved mockup:
- In Settings, Help me choose only suggests. It shows a "Suggested:" header, a dashed "Suggested" card and one honest button: "Use Parakeet v3 + Whisper Large v3 Turbo (downloads 670 MB)".
- The wizard still pre-selects, which is correct there because nothing is saved until its setup button.
- All set shows the right text for downloading, ready and failed.
- A local user's tier rows are muted ("add a key to use").
- The Hindi advice is now conditional.

What is left: the free-option hint added for R2F3 sends a key-free user round in a circle. The command it names does not switch them to local transcription. On the Web, the hint also renders as one run-on line. In fairness, the command came from my own round-2 recommendation, and it was wrong.

## 2. Round-2 findings: status

| Id | Status | Evidence |
|---|---|---|
| R2F1 Settings answer switched the model or downloaded | FIXED | `LocalModelPicker.tsx:136-142`: with `onUseSuggestion` set, an answer only records the suggestion. `:443-455`: only the Use button calls choose. `r3-w5-settings-suggested-1440.png` and `r3-w2-settings-reorder-1440.png` show the "Suggested:" header, the dashed Suggested card and the Turbo card still checked. Proof records no writes after four answers and config unchanged. |
| R2F2 Hindi advice for every Indian language | FIXED | `local_recommend.py:175` says "If your audio is Hindi, …"; the button reads "My audio is Hindi: set language to Hindi" (`LocalModelPicker.tsx:470`); the CLI asks "Is most of your audio Hindi? … (Every recording will then be treated as Hindi.)" (`cli/onboard.py:276`). |
| R2F3 key-free user who skips onboarding | PARTLY | The hint exists and shows in Settings' "Next run" box (`r3-w4-modal-nofit-1440.png`), but see R3F1. |
| R2F4 "typical" desktop | FIXED | `grep typical` over CHANGELOG, README, docs/user, the skill, ui/src, core and cli finds no hits. |
| R2F5 All set text vs status | FIXED | `r3-w1-allset-downloading` shows the "works once it finishes downloading" note; `r3-w1-allset-ready` drops it; `r3-w1f-allset-failed` says "Hindi and other languages won't work until you download Whisper Large v3 Turbo in Settings." |
| R2F6 scratch path in tracked files | FIXED in substance | Three review records (`findings.md:536`, `proof.md:435`, `report-opus-r2.md:90`) still quote the grep command `tmp/claude-1000`: a default user id, no session id, nothing personal. The lead knows; not raised again. |
| R2F7 restart banner assumed a terminal | FIXED (code only) | `LocalSetupNotes.tsx:21` adds "Using the app icon? …". Not walked. |
| R2F8 amber "needs API key" for a local user | FIXED | `r3-w5-settings-rows-1440.png` shows the muted "add a key to use". |
| Also fixed | | The F9 leftover: display names now show in the Model line and the tier rows. The mix advice now says why Parakeet v3 is the main model. |

## 3. New findings, most severe first

**R3F1. should-fix. CONFIRMED (code trace + screenshot).** The free-option hint names a command that does not finish the job, and on the Web it is garbled.

- **Where:**
  - `src/anyscribe/providers/base.py:10-13` (the hint text)
  - `src/anyscribe/core/local_setup.py` (`run_setup` docstring: "Does NOT change settings.provider")
  - `src/anyscribe/core/resolve.py:78-83` (no fallback to local when no key is set)
  - `ui/src/pages/SettingsPage.tsx:1279-1287` and `ui/src/pages/TranscribePage.tsx:384` (plain `<p>`, so the hint's leading `\n` collapses)
- **Scenario (CLI):**
  - A key-free person runs `anyscribe transcribe <url>` without onboarding. They read the warning and the error, both ending "Or transcribe free on this computer, no key needed: `anyscribe local setup --model parakeet-v3`". The hint is printed twice per run.
  - They run that command and see "Local transcription ready. Default model: Parakeet v3."
  - They run `anyscribe transcribe <url>` again. The provider is still `openai` and the quality is still `balanced` (the dataclass defaults; setup never touches them). They get the same warning, the same error and the same hint. It is a loop.
  - The same happens on the Web: the Settings setup window also leaves the provider alone (`SettingsPage.tsx:907-913` only refreshes), so the Next run box keeps showing the warning.
- **Web rendering:** `r3-w4-modal-nofit-1440.png` shows the line as one run-on sentence: "…using openai instead Or transcribe free on this computer, no key needed: `anyscribe local setup --model parakeet-v3` (or Settings, then Local transcription)."
  - The backticks show as literal characters.
  - It tells a person who is already in Settings to go to "Settings, then Local transcription", but no section there has that name; the card is labelled "local".
  - The Transcribe page error box has the same problem, so the hint fails exactly the person R2F3 was meant to help.
- **Fix (smallest):**
  1. Point the hint at the path that does switch the provider: "Or transcribe free on this computer, no key needed: run `anyscribe onboard` and choose On this computer (in the dashboard: Settings, then Run setup wizard)." Both wizards set `provider: local`.
  2. Add `whitespace-pre-line` to the two `<p>` elements.
  3. Optionally, when the provider is not local, `anyscribe local setup` could end with: "To use it for every transcript: `anyscribe config set quality free`."
- **Test:** on an empty HOME, the hint text contains "onboard", and a test asserts the next plan's provider after the step it names.

**R3F2. nit. CONFIRMED (code + screenshots).** The Settings "Tip" gives a Web user a terminal command, and it stays up after it no longer applies.

- **Where:** `core/local_recommend.py:287-300` and `SettingsPage.tsx:1100-1104`.
- **Problem:** "Tip: Parakeet v3 is rated 5/5 … Try it: anyscribe local setup --model parakeet-v3" sits directly above the Parakeet card, which does this in one click.
  - It stays while Parakeet is already "Downloading; becomes your default when done" (`r3-w5-settings-pending-after-reload-1440.png`).
  - It stays after a failed switch (`r3-w3-helper-failed-1440.png`).
- **Fix:** hide it while `pending_default` is set. On the Web, end it with "Try it: click the Parakeet v3 card below." Keep the command for the CLI and MCP.

**R3F3. nit. CONFIRMED (code + proof).** Settings offers "Use" for the model already in use.

- **Where:** `LocalModelPicker.tsx:443-455`.
- **Problem:** a Turbo user who answers "Hindi" or "Something else" gets "Use Whisper Large v3 Turbo (already downloaded)" (the proof records it twice). Clicking it changes nothing.
- **Fix:** when the primary is the current default and every extra is ready, show "This is already your default" instead of the button.

## 4. Answers to the brief

- **Is this the job he asked for, and the simplest instrument?** Yes.
  - It delivers keyless local by default, Spokenly-style cards, and a guide that explains why.
  - Round 3 made it simpler: the server now owns "choose", and three browser copies of the pending/extras logic were deleted.
  - Nothing is gold-plated.
- **Does it read right to its reader?** Yes on every screen I checked, apart from R3F1's hint and the two nits.
  - The mix explanation is clear.
  - Download sizes match the button: 670 MB when Turbo is already present, 1.6 GB in the wizard.
  - The no-fit state says why and what to do ("Free up space, then ask again").
  - The 390 px Settings layout holds.
- **Card numbers (lead evidence 3):** every card set carries "measured on English audio on a 6-core desktop processor … your computer may be faster or slower". That is honest.
- **The WARNING (lead evidence 2):** unreachable on the wizard and onboard paths. A user who skips setup still sees it; that is R3F1.

## 5. Pending owner checks

- **Mac re-measure with the CPU provider forced** (the fix is in, at `local.py:125-127`). The proof still says the lead does it, and I saw no Mac numbers after the fix.
- **mockup.html in the public repo:** it says "your desktop (i5-10600K)" and "transcripts already in your vault". Keep it or mask it? Carried over from round 2.
- **Should a key-free person who skips the wizard default to local?** A bigger change than this PR. My advice: not now; fix the hint (R3F1).

## 6. What I could not check, and what I inspected

**Could not check:**
- No browser or CLI walk. To settle R3F1 on a throwaway HOME with no keys, run `anyscribe local setup --model parakeet-v3 --yes`, then `anyscribe transcribe <short English file>`. I expect the deepgram WARNING plus the OPENAI_API_KEY error, with the hint printed twice.
- `r3-w4-wizard-nofit-1440.png` shows the Parakeet card with an amber border but an empty radio. The code uses one `checked` value for both (`LocalModelPicker.tsx:160-170`), so this is probably a screenshot taken mid colour transition. Re-taking it after 300 ms would settle it.
- R2F7 not walked; it needs a PyAV 19 install.

**Inspected:**
- **Packet:** brief-r3-fit.md, ask.md, lens.md, declined.md, spec.md section 5, diagnosis-r2.md, fix-plan-r2.md, review-log.md, findings.md (round-2 fit report), proof.md (round-2 fixes), mockup.html (text).
- **Screenshots:**
  - `r3-w5-settings-suggested`, `r3-w5-settings-rows`, `r3-w5-settings-pending-after-reload`
  - `r3-w1-mix`, `r3-w1-allset-downloading`, `r3-w1f-allset-failed`
  - `r3-w3-helper-failed`
  - `r3-w4-wizard-nofit`, `r3-w4-modal-nofit`
  - `r3-w9-settings-suggested-390`
  - `r3-w2-settings-reorder`
- **Code:** `LocalModelPicker.tsx` (the cards, HelpMeChoose, the language-check box), `SettingsPage.tsx` (the local card, the notes box, NoteText, the modal hook-up), `providers/base.py` (local_hint), `core/resolve.py`, `config/settings.py` (defaults), `core/local_setup.py`, `cli/local_cmd.py` (setup), `cli/onboard.py` (the Hindi prompt, the where-to-transcribe choice), `core/local_recommend.py` (the reasons, parakeet_suggestion), `LocalSetupNotes.tsx`, `local.py` (CPU provider), the CHANGELOG Unreleased section.
- **Greps:** "typical", the scratch path and i5-10600K across tracked files.

Skipped: engine and guard internals, install paths and test validity (the correctness reviewer's lane).
~~~~~
