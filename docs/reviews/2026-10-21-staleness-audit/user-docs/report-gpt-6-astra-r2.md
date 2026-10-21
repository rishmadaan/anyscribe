**NOT YET.** The main corrections are real, but several pages still contradict them. One revised table introduces a new unsupported claim about Groq’s language picker. Correct the findings below, regenerate the HTML, and verify CI before merging.

Reviewed HEAD `53b864b349880a1045f2dd83deef05dc648e238a` against `b3cddc1`. The diff contains only documentation and landing-page changes. No runtime changes or file deletions were introduced.

All repository paths below are relative to `<checkout>`.

**Prior findings**

| Round-one finding | Status | Evidence |
|---|---|---|
| Correctness D1: batch timeout | FIXED | Wording now acknowledges that the executor waits for the running job; timeout does not cancel it. |
| D2: stdout not guaranteed JSON | PARTLY | Commands now disclose yt-dlp output contamination, but landing still promises clean JSON broadly. See current D2. |
| D3: automation contract | PARTLY | JSON availability is qualified, but non-terminal refusal and structured-error guarantees remain overstated. See D1–D2. |
| D4: uninstall-service effects | FIXED | Revised text matches launchd unload and the tray’s shutdown handling, including stopping its owned server. |
| D5: provider chunking | PARTLY | Cloud-provider exceptions are corrected; troubleshooting still incorrectly includes local transcription. See D7. |
| D6: `data.model` semantics | PARTLY | The JSON explanation is accurate, but other passages still describe a plan as proof of execution. See D4. |
| D7: bare command and missing config value | FIXED | `anyscribe transcribe` and the completed `config set` example match their Typer arguments. |
| D8: language counts | PARTLY | Four catalogue counts are correct; the revised Groq cell incorrectly claims a bundled picker list. See D5. |
| D9: word-level timestamps | FIXED | Revised segment wording matches the roughly 30-word grouping in Deepgram and ElevenLabs. |
| D10: Groq diarization advice | FIXED | Advice now explicitly selects Deepgram with `--provider deepgram --diarize`. |
| D11: network disclosure | FIXED | README now names installation, version checks and automatic yt-dlp upgrades, consistent with updater/dependency code. |
| D12: recovery retry | FIXED | Text distinguishes downloading the URL again from transcribing the saved recovery file directly. |
| D13: provider testing | PARTLY | Detailed explanations are corrected, but provider and onboarding introductions still promise validation. See D3. |
| D14: flag defaults | FIXED | Changed cells reflect configured language/diarization and pinned-model resolution. |
| D15: skill installation trigger | PARTLY | README, agents and landing examples are corrected; command reference still says every invocation. See D6. |
| D16: HOST/GUEST labels | FIXED | Landing sample now uses zero-based speaker labels. |
| Fit D1: landing skill card | FIXED | Card now describes installation on a normal command instead of onboarding specifically. |
| Fit D2: automatic local fallback | FIXED | Revised setup text no longer promises automatic failover. |
| Fit D3: chunking | PARTLY | Same remaining local-transcription overstatement as correctness D5. |
| Fit D4: network disclosure | FIXED | Same evidence as correctness D11. |
| Fit D5: speaker labels | FIXED | Same evidence as correctness D16. |
| `configuration.md:270`: Deepgram speaker detection | DECLINED-OK | Statement is explicitly Deepgram-specific; this application does not require a speaker-count argument. Its acoustic explanation was not independently verified upstream. |

The new defect introduced by the revised wording is current **D5**. The other findings below are incomplete corrections or remaining copies of the same error.

**Findings**

**D1. should-fix · CONFIRMED: Non-interactive commands do not universally refuse confirmation**

Where: `docs/user/commands.md:1155–1160`.

The text says commands refuse to run without `--yes` when no terminal exists. However, `cli/rm.py:45–46` calls `typer.confirm` without checking whether stdin is a terminal. Service commands do likewise unless either `--yes` or `--json` is present (`cli/service_cmd.py:45–46`, `67–68`).

An agent invoking `anyscribe rm existing-slug` with an open input pipe can wait for input instead of receiving the promised refusal. This is a source trace; no deletion command was executed.

Replace the bullet with:

> **`--yes` (`-y`) skips confirmation.** Pass it when scripting commands that ask for confirmation. Some commands explicitly reject non-interactive use without it; `rm`, `install-service`, and `uninstall-service` instead attempt to read a confirmation. The two service commands also skip confirmation with `--json`.

**D2. should-fix · CONFIRMED: Machine-readable output is still promised where it is unavailable**

Where: `landing/index.html:1535–1536`, `1661`; `docs/user/commands.md:1255`, `1301`.

Concrete failures:

- `anyscribe doctor --json` is rejected because `doctor()` declares no such option.
- `anyscribe doctor` produces a human-readable report, despite the “machine-readable health snapshot” description.
- Headless onboarding without `--json` can emit a plain-text exit-2 error; its error branches check `output_json`.
- Even supported transcription JSON can be preceded by yt-dlp upgrade output, as the newly added caveat correctly explains.

Replace the landing heading with:

> JSON for scripting

Replace its accompanying paragraph with:

> Transcription and many result-reporting commands accept `--json`. Check each command’s flags. Some startup messages can still appear on stdout.

Replace the opening claim at landing line 1661 with:

> JSON output on supported commands, with documented limits.

Replace the onboarding error sentence with:

> With `--json`, headless validation errors are reported as JSON on stderr. Argument-parsing errors may still be plain text.

Replace the doctor sentence with:

> For a human-readable health report to attach to a bug report, `anyscribe doctor` covers dependencies, config, installation, and updates.

**D3. should-fix · CONFIRMED: Provider checks still promise more validation than they perform**

Where: `docs/user/providers.md:461`; `docs/user/commands.md:44`; `docs/user/getting-started.md:91`.

`cli/config_cmd.py:330–363` loads the provider and checks whether a key is present. It makes no authentication request. The web test also returns success for a nonempty Groq or Sarvam key without validating it (`web/routes/config.py:297–300`).

A user entering a bogus Groq key can receive success, follow “so you know it works,” and encounter their first authentication failure only during transcription.

Exact replacements:

- Providers introduction:

  > Check that a provider loads and its API key is set. This does not validate the key or available credit:

- Commands overview description:

  > Check provider loading and key presence

- Getting-started step:

  > **Paste your API key.** The **Test key** button performs a provider check where available; for Groq and Sarvam it only confirms that a key was entered. Success does not guarantee that transcription will succeed. This step is skipped for `local`.

The stale runtime help text is outside this docs-only change, but user documentation can accurately describe the existing behavior.

**D4. should-fix · CONFIRMED: Configuration and planned models are still presented as execution evidence**

Where: `docs/user/commands.md:208`, `600`, `1280`; `docs/user/troubleshooting.md:337`.

The new `data.model` caveat is correct, but these passages contradict it.

For example, a Deepgram run with `--language hi-Latn` can resolve to `nova-3` while `providers/deepgram.py:47` sends `nova`. Separately, running `anyscribe config --json` after a transcription with per-run overrides reports current defaults, not the previous run.

Replace the command-reference descriptions with:

> **provider · model:** the plan selected for this run. Read the notes for provider-specific model substitutions.

> **Next run:** the provider and planned model selected from current defaults, plus the reason and any substitution notes.

> The `resolved` block describes a run using current defaults. Per-run flags and provider-specific substitutions can change the model used.

Replace the troubleshooting heading and add the qualification:

> **Check what the current defaults would select:**

> This does not reconstruct a previous run or its per-run flags. Use that run’s output and notes when diagnosing it.

**D5. should-fix · CONFIRMED: Revised Groq language cell describes a picker list that is not registered**

Where: `docs/user/providers.md:151`, `160`.

The revised table gives Groq “100 codes (Whisper’s list)” and explicitly defines the numbers as what the language picker offers.

Recounted from the actual lists:

| Catalogue | Entries | Unique codes |
|---|---:|---:|
| Whisper | 100 | 100 |
| Deepgram | 89 | 89 |
| ElevenLabs | 92 | 92 |
| Sarvam | 23 | 23 |

Sarvam’s 23 includes English, so “22 Indian + English” is correct.

However, `providers/languages.py:357–364` has no Groq entry. Consequently, `/api/providers/groq/languages` returns an empty list with `freeform: false` through `web/routes/config.py:177–178`.

Replace the Groq cell with:

> No bundled picker list

Add:

> Groq currently has no registered language-picker list. Use `--language` to supply a language code.

**D6. nit · CONFIRMED: One skill-installation guarantee still says every invocation**

Where: `docs/user/commands.md:1002`.

The revised README correctly excludes top-level `--version` and `--help`, but this tip still promises auto-update on every invocation. The eager version callback exits before the main callback; migration also bypasses the silent updater.

Replace the tip with:

> You usually do not need to run this manually. When `~/.claude` exists, normal commands such as `anyscribe ui` install or refresh the skill when its recorded version differs. Top-level `--version` and `--help` do not trigger this. Use `--force` to repair an existing copy.

**D7. nit · CONFIRMED: Long-file troubleshooting still includes local transcription in cloud chunking**

Where: `docs/user/troubleshooting.md:350–353`.

“Anything over 30 minutes (or 25 MB)” includes local files transcribed locally. But `providers/local.py:99–104` passes the complete file to faster-whisper without the application’s cloud chunking/checkpoint path.

Replace the paragraph with:

> Most cloud providers split audio over 25 MB or 30 minutes into roughly 18-minute pieces. Sarvam uses pieces up to 28 seconds. OpenAI diarization refuses files over either limit. Local transcription does not use this cloud chunking path.

Regenerate the corresponding `landing/docs/*.html` after these edits.

**Answers to the brief**

- **Right job and instrument:** Yes. Correcting source Markdown and the hand-written landing page, then regenerating documentation HTML, is appropriate. No behavioral changes were smuggled into this PR.
- **Commands:** Changed concrete command examples trace to accepted Typer commands and arguments, including explicit `transcribe --clipboard`, populated `config set`, batch timeout/resume, local setup, and onboarding’s long-form `--model`. The remaining broad promises about commands are identified above.
- **JSON:** The corrected transcription example matches the `success/data/error` envelope and transcription fields. Batch uses the same envelope with its own summary fields. The scripting lookup is correctly `.data.file`.
- **Chunking:** OpenAI ordinary transcription, Groq, Deepgram, ElevenLabs and OpenRouter use the shared size/duration threshold; OpenAI diarization refuses oversized input; Sarvam uses 28-second pieces. Local is the remaining wording exception.
- **Generated HTML:** Read the renderer and checked five changed passages across Markdown and committed HTML: timeout behavior, model semantics, confirmation contract, recovery retry and catalogue explanation. Those passages match. This is not proof of full fresh-render equality.
- **Installed skill:** `install-skill` copies the bundled `src/anyscribe/skill` files. This PR does not repair that separate copy; the audit explicitly assigns it to the skill PR. The overall audit cannot be called complete from this docs PR alone.

**Pending owner checks**

None. The remaining corrections and verification belong to the lead. The settled Deno and Python-support decisions were not reopened.

**Checks not run**

The brief prohibited application execution, tests, builds, installations and network calls. Therefore live transcription, visual rendering, full generated-file equality and CI status remain unverified. External prices, credits and upstream service capabilities were not independently checked.

From the checkout, the lead can run these checks in the prepared CI environments:

```bash
gh pr view 17 --json headRefOid,statusCheckRollup
gh pr checks 17

python scripts/build-docs.py
git diff --exit-code -- landing/docs
python scripts/check-docs.py

ruff check src tests scripts
pytest
python -m build
bash scripts/rehearse-migration.sh

npm --prefix ui ci
npm --prefix ui run lint
npm --prefix ui run build
git diff --exit-code -- src/anyscribe/web/static
```

The Python workflow runs on both Python 3.10 and 3.12. Confirm that CI results belong to the reviewed SHA or its corrected successor. `git diff --check b3cddc1 HEAD` passed during this review.

**Inspected**

The brief, saved diff, audit/spec and implementer report; README; all six user-doc Markdown files; landing page and generated documentation HTML; CLI, providers, language catalogues, core modules, web routes and settings; Python documentation scripts and workflows; CHANGELOG and BACKLOG; bundled skill and its references. No files were changed, and `tests/`, `.cache/` and `ui/node_modules/` were left alone.