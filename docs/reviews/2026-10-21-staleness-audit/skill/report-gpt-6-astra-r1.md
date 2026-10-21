**NOT YET.** PR #18 fixes the main audit issues, but the bundled guide still contains rejected commands and claims stronger than the implementation supports. Several were inherited from the audit specification itself. Merge also requires green CI on the exact reviewed SHA.

Reviewed head: `0b90724626fe451c0c4740fce5aad7c2e7aa1be5`, against `b3cddc1`.

All repository paths below are relative to:
`<checkout>`.

**Findings, most severe first**

1. **S1 · should-fix · CONFIRMED: The skill’s blanket flag rule produces rejected commands.**

   Where: `src/anyscribe/skill/SKILL.md:36`.

   The instruction to “always use `--json --quiet`” applies to every command. However, `config --json --quiet`, `local setup --model base --yes --json --quiet`, and `providers test deepgram --json --quiet` all fail argument parsing with exit 2. I reproduced these failures using the checkout’s actual command signatures, with command bodies disabled.

   This predates the PR, but directly undermines the corrected decision tree.

   Replace with:

   > For transcribe, download, and batch, use `--json --quiet`. For other commands, use only the flags documented for that command. Some support `--json` without `--quiet`; others return human-readable output only.

2. **S2 · should-fix · CONFIRMED: A newly added API-key repair command lacks its required value.**

   Where: `src/anyscribe/skill/references/troubleshooting.md:228`.

   Substituting `openai` into `anyscribe config set <provider>_api_key` produces `anyscribe config set openai_api_key`, which exits 2 because `VALUE` is required. This follows the audit’s proposed wording, so the specification was wrong here.

   Evidence: `cli/config_cmd.py:182`, especially the required `value` argument at line 186. Isolated argument parsing reproduced exit 2.

   Replace the command with:

   > `anyscribe config set <provider>_api_key YOUR_KEY`

3. **S3 · should-fix · CONFIRMED: The JSON documentation misidentifies planned models as models that actually ran.**

   Where: `src/anyscribe/skill/references/commands.md:90` and `:626`.

   Concrete counterexamples:

   - OpenAI with `--diarize`: JSON reports `plan.model`, commonly `gpt-transcribe`; the provider sends `gpt-4o-transcribe-diarize`.
   - Deepgram with `--language hi-Latn`: JSON can report `nova-3`; `_build_params()` sends `nova`.
   - A cached result reports the current plan’s model even though no model ran.
   - Local onboarding returns `model: null`, not the selected Whisper size.
   - Onboarding with an explicit quality tier reports the configured provider’s model, without resolving the tier.

   Evidence: `cli/transcribe.py:142`, `cli/batch.py:174`, `core/resolve.py:115`, `providers/openai.py:83`, `providers/deepgram.py:47`, `core/onboard_headless.py:278`.

   Replace the transcription explanation with:

   > `model` reports the model selected by the run planner. Provider-specific overrides can differ: OpenAI diarization uses `gpt-4o-transcribe-diarize`, and Deepgram hi-Latn uses `nova`. Read `notes` for these overrides. For cached results, no model runs and this field does not identify the model that created the saved transcript.

   Replace the onboarding explanation with:

   > `model` is the configured provider’s pinned or default cloud model, or `null` for local. It does not resolve quality-tier routing. After setup, use `anyscribe config --json` to inspect the next-run plan and `anyscribe local status --json` for the default local model.

4. **S4 · should-fix · CONFIRMED: The new OpenAI recovery advice can repeat the same failure.**

   Where: `src/anyscribe/skill/references/troubleshooting.md:271`.

   A user who ran `anyscribe "recording.mp3" -p openai --diarize` can add a Deepgram key and retry exactly as advised, but `-p openai` still wins over automatic routing. Also, dropping `--diarize` does not disable a persisted `diarize: true` setting.

   Evidence: explicit-provider precedence in `core/resolve.py:55`; persisted diarization is combined with the flag before routing.

   Replace with:

   > After setting a Deepgram key, retry the original source with `-p deepgram --diarize`, replacing any existing provider flag. To use OpenAI without speaker labels, omit `--diarize`; if `diarize` is enabled in config, first run `anyscribe config set diarize false`.

5. **S5 · should-fix · CONFIRMED: Download failures do not carry a failed pip command and stderr.**

   Where: `src/anyscribe/skill/references/commands.md:556`, `:628`; also `SKILL.md:131`.

   If faster-whisper is already installed and Hugging Face downloading fails, the result has `phase: "download"` and a top-level `error`. The nested `install` describes the successful or already-installed package state; its command may be `null`, and it has no failure stderr.

   The new wording tells an agent to inspect the wrong fields.

   Evidence: `core/local_setup.py:260` versus `:282`.

   Replace the setup explanation with:

   > With `--json`, setup failures are NDJSON records on stdout. Inspect `phase`: installation failures carry `install.command` and `install.stderr`; model-download failures carry `error`, while `install` describes the preceding installation step.

   For onboarding, use the same distinction under `local_setup`.

6. **S6 · should-fix · CONFIRMED: The JSON examples still imply a stronger output contract than exists.**

   Where: `src/anyscribe/skill/references/commands.md:68`, `:94`, `:205`.

   The corrected envelopes match the normal output paths, but:

   - A missing local input fails in `_validate_input()` before the transcription JSON error handler.
   - A missing batch list prints only stderr and exits 1.
   - An empty or fully resumed batch exits 0 without a JSON summary.
   - Automatic yt-dlp updating prints progress to stdout, even during `--json --quiet`, so stdout need not be one parseable JSON document.

   Evidence: `cli/transcribe.py:92`, `cli/batch.py:46`, `:57`, `:81`, and `core/deps.py:301`.

   Add:

   > These examples describe completed transcription and batch-processing paths. Input and usage errors can produce stderr without JSON; empty or fully resumed batches can exit successfully without a JSON summary. Automatic yt-dlp updates can also prepend progress text to stdout despite `--quiet`. Check exit status and output before treating stdout as one JSON document.

   Making all paths consistently machine-readable would be a separate behavior fix.

7. **S7 · should-fix · CONFIRMED: The documented batch timeout is not a wall-clock cap.**

   Where: `src/anyscribe/skill/SKILL.md:311`; `references/commands.md:201`, `:233`.

   The code raises a timeout inside a `with ThreadPoolExecutor(...)` block. Exiting that block waits for the worker to finish. Consequently, `--timeout 300` can wait substantially longer than five minutes, and the worker can complete API calls and write a transcript before the URL is reported failed.

   Evidence: `cli/batch.py:257–264`. This is an existing implementation limitation, not a regression introduced here.

   Replace the timeout guidance with:

   > `--timeout` marks a URL failed when its processing exceeds the threshold, but currently does not cancel the worker or bound elapsed time. The batch waits for that worker to finish before advancing, and the worker may still write a transcript.

   Remove the “Cap each URL at 5 minutes” example comment.

8. **S8 · should-fix · CONFIRMED: Service instructions understate immediate start and stop effects.**

   Where: `src/anyscribe/skill/references/commands.md:388`; `references/troubleshooting.md:343`.

   The guide says these commands only toggle login startup and do not stop a running tray. The implementation loads a plist with `RunAtLoad=true`; uninstall unloads that LaunchAgent. A tray managed by that agent can therefore start immediately on installation and stop on removal, including its owned server through signal teardown. A manually launched tray is a different case.

   Evidence: `core/service.py:44`, `:63`, `:72`; `cli/tray_cmd.py:165`.

   Replace with:

   > Installation loads the LaunchAgent and can start the tray immediately as well as at login. Removal unloads the LaunchAgent and can stop a tray it manages, including the server that tray started. A manually launched tray must be quit separately. Neither command uninstalls anyscribe.

9. **S9 · should-fix · CONFIRMED: The new uncached-model guidance contradicts the remaining setup-only download guarantee.**

   Where: `src/anyscribe/skill/references/providers.md:199`.

   The PR correctly says an uncached local model downloads on its first use, but this paragraph still says nothing downloads unless the user runs setup. With faster-whisper already installed, selecting an uncached `local_model` and transcribing reaches `WhisperModel(MODEL_REPOS[model_size], ...)` without a setup gate.

   Evidence: `providers/local.py:67–88`; the newly corrected guidance at `references/providers.md:245`.

   Replace with:

   > Transcription runs on-device without an API key. Package installation and model downloads require internet. Download the selected model before going offline; choosing an uncached size can trigger a download on the next local run.

10. **S10 · nit · CONFIRMED: The replacement batch JSON example has inconsistent totals.**

    Where: `src/anyscribe/skill/references/commands.md:211`.

    It reports three results and two successes, but contains only one successful row and one failed row. The JSON parses, but the example cannot represent the shown complete result list.

    Fix: change `"total": 3` to `"total": 2` and `"succeeded": 2` to `"succeeded": 1`, or add the missing successful row.

11. **S11 · nit · CONFIRMED: Relative-path restrictions are overstated.**

    Where: `src/anyscribe/skill/SKILL.md:291`; `references/commands.md:252`.

    Relative paths work from any current directory when they correctly locate a file inside the workspace’s `sources/` tree. They are not restricted to running from the workspace directory.

    Evidence: `vault/index.py:143` expands `~` and checks the supplied path relative to the current directory; deletion separately enforces workspace containment.

    Replace with:

    > Relative paths are resolved from the current working directory, not from the workspace root. Prefer the `data.file` path returned by transcription.

**Answers to the brief**

The PR is the right instrument for the owner’s request: it corrects the packaged operator guide that `install-skill` copies into `~/.claude/skills/anyscribe/`. However, applying all 39 audit recommendations does not establish correctness. S2 follows a faulty recommendation; S3 and S5 show claims the audit did not qualify adequately.

I traced the following examples through `cli/main.py` registration and their subcommand signatures. Isolated Typer parsing accepted all of them. Command bodies and startup hooks were disabled, so acceptance proves syntax, not operational success.

| Example | Handler |
|---|---|
| `anyscribe transcribe --clipboard` | `transcribe.py:transcribe` |
| `anyscribe transcribe` | `transcribe.py:transcribe` |
| `anyscribe --debug transcribe "https://youtu.be/abc123"` | Root callback, then `transcribe` |
| `anyscribe local setup --model base --yes --json` | `local_cmd.py:local_setup` |
| `anyscribe config set provider local` | `config_cmd.py:config_set` |
| `anyscribe config set quality free` | `config_cmd.py:config_set` |
| `anyscribe config --json` | `config_cmd.py:config_main` |
| `anyscribe providers test deepgram` | `config_cmd.py:providers_test` |
| `anyscribe install-service --yes --json` | `service_cmd.py:install_service` |
| `anyscribe uninstall-service --yes --json` | `service_cmd.py:uninstall_service` |
| `anyscribe install-skill --force` | `skill_cmd.py:install_skill` |
| `anyscribe rm "~/anyscribe/sources/youtube/my-video.md" --yes --json` | `rm.py:rm` |
| `anyscribe "https://youtu.be/abc123" -p deepgram --language hi` | Bare-input routing, then `transcribe` |
| `anyscribe onboard --provider openai --model whisper-1 --yes --json` | `onboard.py:onboard` |
| `anyscribe model info large-v3-turbo --json` | `models_cmd.py:model_info` |

Other requested checks:

- **JSON fields:** The normal transcription envelope matches all documented fields. Batch envelope and per-item keys match, apart from the example’s inconsistent counts. The `rm` envelope matches. Local setup’s NDJSON stream and status payload match the code, subject to S5. All ten listed onboarding result keys exist; their model semantics need S3’s qualification.
- **Troubleshooting strings:** The new headings match emitted prefixes or clearly substituted placeholders from preflight, API classification, OpenAI, Groq, YouTube, and Instagram. Matching an error string does not establish that its proposed repair works; S2 and S4 are counterexamples.
- **Model repositories:** All seven `MODEL_SIZES` have corresponding `MODEL_REPOS` and `MODEL_SPECS` entries. `model_info()` validates the size before indexing. Turbo resolves to `dropbox-dash/faster-whisper-large-v3-turbo`; distil resolves to `distil-whisper/distil-large-v3.5-ct2`.
- **New test:** It asserts repository identity, not a count. It covers turbo specifically. The reported mutation failure is credible from inspection, but I did not rerun it.
- **License:** The first 14 skill lines retain the copyright, license identifier, grant, warranty notice, and license link. The installer and license files are unchanged. No apparent conflict with `test_skill_license.py`.
- **Behavior changes:** The repository lookup changes `model info` output as intended. The Groq URL changes authentication-error guidance. The remaining production changes are help strings, documentation, or comments. No files were deleted.
- **Installed copy:** Updating an editable checkout without changing the package version does not automatically refresh an installed skill whose `.version` already matches. The documented `anyscribe install-skill --force` is therefore necessary when verifying this unreleased branch.
- **Same-pattern residues:** `providers/openai.py:113` still claims Deepgram handles large files natively; `core/quality.py:23` still says “no chunking”; `mcp/server.py:460` still promises a connectivity test without making a request. These are pre-existing follow-up corrections, not newly introduced behavior.

**Pending owner checks**

None. The findings and verification work belong to the implementation lead. Deno and Python 3.10 decisions remain outside this review, as instructed.

**Verification limits and inspection record**

I read the brief, complete saved diff, audit specification, implementer report, all named CLI/provider/core/web-route Python sources, settings, scripts, workflows, skill files, the two named tests, CHANGELOG, and BACKLOG. I also traced the audit’s referenced path, vault-index, downloader, and MCP files.

Completed read-only checks:

- Reconfirmed the exact head SHA.
- `git diff --check b3cddc1..HEAD` passed.
- AST parsing passed for the 56 Python files in the brief’s source patterns.
- Every fenced JSON example in the bundled Markdown parsed.
- Isolated argument parsing used Typer `0.27.0`, without importing application modules or executing their callbacks.

Per the brief, I did not run tests, builds, installation, servers, network requests, or mutations. The implementer’s “485 passed, 1 skipped” remains an unverified report. These checks remain for the lead, from the reviewed checkout:

```bash
ruff check src tests scripts
pytest
pytest tests/test_local_cli.py::test_model_info_repo_matches_model_repos tests/test_skill_license.py
python -m build
bash scripts/rehearse-migration.sh
python scripts/build-docs.py
git diff --exit-code landing/docs
python scripts/check-docs.py
npm --prefix ui ci
npm --prefix ui run lint
npm --prefix ui run build
git diff --exit-code -- src/anyscribe/web/static
gh pr view 18 --json headRefOid,statusCheckRollup
```

Require the CI results to correspond to the reviewed SHA, or review the replacement SHA after fixes. Live provider claims, pricing, performance estimates, Claude Code permission-pattern behavior, and platform-specific installation behavior were not verified.