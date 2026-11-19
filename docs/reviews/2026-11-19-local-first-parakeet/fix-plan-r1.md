# Fix plan, round 1 (lead's choices; binding where it decides)

Fix every UPHELD finding in review-log.md at the lead's grade. C3/F10 are
already done by the lead (scratch paths masked, screenshots moved out of the
repo); do not commit screenshots to the repo again: save new ones to
`~/.review-runs/2026-11-19-local-first-parakeet/screens/` and name them in proof.md.

1. **C1/F1 stale quality.** TranscribePage sends `quality` only when the
   person changed it on that page in this session; otherwise the server uses
   the saved config. The page refetches config when the onboarding wizard
   closes. No submit before config has loaded. Test: the wizard-then-transcribe
   path yields no WARNING in the job's plan notes. Deliberate cloud-tier
   choices keep their warnings.

2. **C2/F4 language check.** Replace the single opening-window check:
   - Detect on speech only, at up to three windows spread across the
     recording (start, middle, end of the speech-bearing audio; fewer for short
     files). Use faster-whisper's own facilities where they fit
     (`detect_language(..., vad_filter=True)`), or the silero VAD already
     loaded for Parakeet.
   - Route to Whisper if ANY window's top language is outside the chosen
     Parakeet model's set.
   - Unsure (every window's top probability below 0.5, or no speech found):
     use Whisper when a suitable one is ready; otherwise run Parakeet and add
     a note saying the language check was unsure.
   - Whisper-only runs (default model is Whisper, language `auto`) go back to
     the old behaviour: do not force a detected language into Whisper. The
     English punctuation prompt still needs a language decision first: use a
     VAD-filtered detection on the already-loaded model for that, and pass
     `language=None` unless the person set one.
   - On the Parakeet-to-Whisper fallback, keep passing the detected language
     (measured better than Turbo's own auto on short Hindi clips).
   - Wording everywhere (CHANGELOG, docs, picker explainer, recommendation
     text): "checks the language at the start, middle and end of each
     recording". Drop "never writes gibberish". For the "A mix" answer, keep
     Parakeet v3 + Turbo, and add one sentence: "If one recording switches
     language mid-sentence (Hinglish), make Whisper Large v3 Turbo your
     default instead."
   - Real-engine proof: a clip made of 35 s of English speech followed by
     Hindi (concatenate the two test clips) routes to Whisper; a clip with
     10 s of leading silence then English stays on Parakeet.

3. **C4 Mac speed.** Pass `providers=["CPUExecutionProvider"]` to both
   `onnx_asr.load_model` and `onnx_asr.load_vad`. Comment:
   `# shortcut: CoreML partial support made load 110 s and runs 7x slower on
   Apple silicon (measured 2026-11-19); revisit if onnx-asr ships a full CoreML path`.
   Add a test that asserts the providers argument. The lead re-measures on the Mac.

4. **C5 readiness.** Separate "some bytes on disk" from "ready": a model is
   ready only when every file it needs is present (no `.incomplete` blobs; the
   required file list per repo). Pull always calls the downloader (it resumes
   and is a no-op when complete) instead of skipping on any bytes. The guard's
   fallback, default activation and the card's "downloaded" state use
   readiness; a partial model shows as "incomplete: resume download".
   Choosing a Parakeet model as default (any surface) ensures Tiny + VAD are
   ready, downloading them visibly if not.

5. **C6/F3 the second download.** State sizes up front: the suggestion says
   "downloads 670 MB + 1.6 GB"; the wizard button says "Download Parakeet v3 +
   Whisper Large v3 Turbo (2.3 GB)". The All set screen lists both models
   with live progress for any still downloading and shows a failure if one
   fails; its wording says Hindi switching works once Turbo finishes. The
   setup modal does the same. CLI names both with sizes and shows progress.

6. **C7 low disk.** Build reasons from the final feasible pick. When nothing
   fits, return an explicit "not enough free space" result naming how much is
   needed. For "mix", prefer a fitting multilingual model over dropping the
   only fallback.

7. **C8/F6 claims.** One caption under the cards on every surface that shows
   them: "Speed and accuracy measured on English audio on a 6-core desktop
   processor without a graphics card. Your computer may be faster or slower."
   The recommendation's comparison says "about 4 times faster on that desktop".

8. **C9 notes.** Restore `notes` from cached frontmatter; print per-file notes
   in human batch output.

9. **C10 restart.** When setup changes a package that is already imported in
   the running process (av, faster_whisper, onnx_asr), the result carries
   `restart_needed: true` and every surface says "Restart anyscribe to finish
   setting up local transcription" (Web UI: visible banner with what to do;
   CLI: printed line). Do not attempt in-process reloads.

10. **C11 pending default.** Any explicit model choice clears a pending
    default; completion applies only the latest accepted choice.

11. **F2 pre-select.** Answering the language question applies the
    suggestion immediately (selects the primary, marks any second model for
    download). Remove the "Use this" / "Selected" button.

12. **F5 reasons.** Rewrite per the reviewer: "Something else" gets its own
    branch (Turbo, 95+ languages, no Hindi wording); English: "As accurate as
    Whisper Large v3 Turbo on English, and about 4 times faster on that
    desktop"; cite memory or disk only when it changed the pick. Hindi or
    Indian answer: offer one-click "Set my language to Hindi" (Web) and a yes/no
    prompt (CLI), explaining it in one line (Turbo is about 3 times more
    accurate on Hindi when told the language). The switch note ends with
    "To skip the check, set your language to <Language> in Settings."

13. **F7 first-run line.** Settle it on a fresh HOME; either way render the
    size and time from the registry data so the line never depends on a slow call.

14. **F8 docs.** getting-started "What you need" leads with local (Parakeet
    v3, no key); cloud second.

15. **F9 nits.** Step numbers count only the steps on the chosen path;
    display names everywhere a model is named to a person (All set summary,
    result card, CLI final line); one size per card (when downloaded show the
    disk size and hide the download size); an undownloaded card's click starts
    its download and says so in words on the card ("Downloading; becomes your
    default when done"); icon-only buttons get visible text labels.

Proof: one proof.md entry per finding id (C1..C11, F1..F9), per the
fixer's brief. Mutation-test every new guard (C2 any-window routing, C4
providers, C5 readiness, C11 latest-choice), asserting identity.
