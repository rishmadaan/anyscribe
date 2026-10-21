**NOT YET.** Three should-fix documentation gaps remain at `5298f4309011aadc66acabdba5872adce1060c26`. CI on this exact SHA is also unverified.

The PR is the right instrument for the owner’s request: it corrects the bundled operator skill and related CLI output. I found no unrelated processing change or deleted file.

**Earlier findings**

| Earlier finding | Status | Evidence |
|---|---|---|
| Astra S1 / Opus S5: local default with saved diarization | **PARTLY** | The detailed recipes now resolve to local after clearing `diarize`; `SKILL.md:70` still gives the incomplete shortcut. See S1. |
| Astra S2 / Opus S2: temporary filename and saved diarization in OpenAI recovery | **FIXED** | Rendered the error with a dummy 30 MB path. No basename appears; the non-diarized alternative explicitly clears saved diarization. A further model-flag case remains, S2. |
| Astra S3 / Opus S1: per-word timestamp claims | **FIXED** | The named skill and CLI claims now say segment timestamps. Parser probes confirm grouping. The replacement troubleshooting sentence introduces a narrower overclaim, S4. |
| Astra S4 / Opus S4: installation “only by local setup” | **FIXED** | `providers.md:199` now names onboarding and Web UI installation paths, consistent with their calls into local setup. |
| Opus S3: Groq long-file error differs | **FIXED** | `troubleshooting.md:275` now describes the inherited OpenAI error accurately. |
| Opus S6: leftover Instagram password | **FIXED** | `SKILL.md:348` explicitly includes older installs. |
| Groq error-check reorder | **DECLINED-OK** | Still deferred; the current ordering is documented. |
| React ElevenLabs blurb | **DECLINED-OK** | Still deferred. The shipped static bundle retains that claim, so the correction is not product-wide. |

**Findings, most severe first**

**S1. should-fix, CONFIRMED: the short offline recipe still selects a cloud provider.**

Where: [src/anyscribe/skill/SKILL.md:70](<checkout>/src/anyscribe/skill/SKILL.md:70).

With saved `diarize: true` and a Deepgram key, following the table’s instruction to set `provider local` leaves the next run on Deepgram. I executed the extracted resolver with those inputs:

```text
provider=local, quality=custom, diarize=true
=> provider=deepgram, via=diarize
```

The detailed recipe at line 134 works, but the decision table still promises the result without its necessary prerequisite.

Replace the table’s command cell with:

> `anyscribe local setup --model base --yes --json` prepares local transcription only. To make it the default, ask before changing an existing provider, then run `anyscribe config set diarize false` followed by `anyscribe config set provider local`. Confirm `resolved.provider` is `local` with `anyscribe config --json`.

**S2. should-fix, CONFIRMED: the revised Deepgram retry can retain an incompatible model flag.**

Where: [src/anyscribe/providers/openai.py:115](<checkout>/src/anyscribe/providers/openai.py:115), also `src/anyscribe/skill/references/troubleshooting.md:271`.

Concrete original command:

```bash
anyscribe "long-recording.mp3" -p openai -m whisper-1 --diarize
```

After the over-limit error, replacing the provider as instructed produces:

```bash
anyscribe "long-recording.mp3" -p deepgram -m whisper-1 --diarize
```

The resolver rejects this before transcription:

```text
Unknown model 'whisper-1' for provider 'deepgram'. Available: nova-3, nova-2
```

Removing the model flag resolves successfully to Deepgram. This is a newly identified recovery gap, separate from the fixed temporary-filename problem.

Use this wording in both places:

> Retry your original URL or file path with `-p deepgram --diarize`, replacing any existing provider flag and removing any per-run `-m` or `--model` flag.

Apply the same model-removal instruction to the Groq provider-switch advice.

**S3. should-fix, CONFIRMED: the Groq recovery advice repeats the saved-diarization omission.**

Where: [src/anyscribe/skill/references/troubleshooting.md:275](<checkout>/src/anyscribe/skill/references/troubleshooting.md:275).

The paragraph offers “drop `--diarize`” as a recovery. With saved `diarize: true`, removing that flag does nothing: `cli/transcribe.py` only sets the value when the flag is present; it never clears the saved value. The orchestrator still passes `diarize=True`, and Groq rejects it again.

Replace that alternative with:

> To keep using Groq without speaker labels, omit `--diarize`; if diarization is enabled in config, first run `anyscribe config set diarize false`.

This is the same bug class already corrected in the OpenAI recovery instructions.

**S4. nit, CONFIRMED: the timestamp replacement claims more than the parsers establish.**

Where: [src/anyscribe/skill/references/troubleshooting.md:166](<checkout>/src/anyscribe/skill/references/troubleshooting.md:166).

The new sentence says Deepgram and ElevenLabs use approximately 30-word segments, “so they are not finer than Whisper’s segments.”

Deepgram instead groups by speaker turn when diarization is enabled. A synthetic response containing 60 alternating-speaker words produced 60 diarized segments, versus two without diarization. The code establishes no universal granularity comparison with Whisper.

Replace the first sentence with:

> Without diarization, anyscribe groups Deepgram and ElevenLabs timing entries into approximately 30-word segments. With diarization, Deepgram segments follow speaker turns. These outputs expose segment timestamps rather than individual word timestamps.

**Verification and answers to the brief**

- **Command parsing:** 21 representative forms parsed through Typer definitions extracted from this checkout. They included clipboard transcription, global debug placement, local setup/teardown, configuration changes, service commands, skill installation, transcript removal, model commands, onboarding, and batch flags. Both old invalid forms were rejected: `anyscribe --clipboard` and onboarding with `-m`.
- **Method boundary:** command bodies were replaced with inert bodies for parsing, preventing startup hooks, configuration writes, downloads, and service operations. Resolver and provider probes executed extracted functions with synthetic inputs. These were not end-to-end CLI runs.
- **JSON:** traced transcribe and batch envelopes and their nested fields, batch result variants, `rm.data.deleted`, local setup NDJSON and phase-specific failures, local status fields, and onboarding result/error fields. The corrected examples match those code paths, subject to the documented non-JSON early exits.
- **Error strings:** the new troubleshooting headings match the corresponding message prefixes, with documented placeholders for provider names, sizes, and status codes. The Groq long-file explanation matches the inherited branch order.
- **Model repositories:** executed the actual `model_info` body with harmless configuration/cache substitutes for all seven sizes. Every returned repository matched `MODEL_REPOS`, including turbo and distil.
- **Regression assertion:** `test_local_cli.py:317` checks repository identity, not a count. The previous hardcoded turbo repository differs from the expected value. I did not execute pytest or a mutation test.
- **License:** the first 14 skill lines retain the required copyright and license identifiers. Bundled and project license contents match. Installer copying was traced, not executed.
- **Installed copy:** `install-skill` copies the package’s `src/anyscribe/skill` content to `~/.claude/skills/anyscribe`. Automatic refresh is version-based; testing this unreleased checkout against an existing same-version installation requires the documented `install-skill --force`.
- **Scope:** beyond output text, the substantive correction is the repository lookup used by `model info`. No transcription-routing or installation dependency change was found. Python syntax parsing passed for 57 scoped files; `git diff --check b3cddc1 HEAD` passed.

**Pending owner checks:** None. Fixes and CI verification belong to the lead, not the owner. The settled Deno and Python-version decisions remain outside this review.

**Checks not run**

The brief prohibits tests, builds, installations, network calls, and writes. The implementer’s reported results therefore remain unverified here. The lead should verify the PR head and CI:

```bash
gh pr view 18 --repo rishmadaan/anyscribe --json headRefOid,statusCheckRollup
gh pr checks 18 --repo rishmadaan/anyscribe
```

Relevant exact local checks, from the reviewed checkout:

```bash
ruff check src tests scripts
pytest
python -m build
bash scripts/rehearse-migration.sh
python scripts/build-docs.py
git diff --exit-code landing/docs
python scripts/check-docs.py
npm --prefix ui ci
npm --prefix ui run lint
npm --prefix ui run build
git diff --exit-code -- src/anyscribe/web/static
```

Require passing CI for the final reviewed SHA, including both configured Python versions. Live provider behavior, external pricing claims, and Claude’s `allowed-tools` matching were not verified.

Inspected the brief, saved diff, audit specification, implementer report, all five bundled skill documents, scoped CLI/provider/core/web-route Python files, settings and paths, MCP server, relevant downloader and vault code, both named tests, both Python scripts, CI/publish workflows, `CHANGELOG.md`, and `BACKLOG.md`. No files were changed.