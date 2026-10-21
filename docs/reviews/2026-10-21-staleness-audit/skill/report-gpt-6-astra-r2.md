**NOT YET.** Three correctness issues remain: the local-default instructions can still select a cloud provider, OpenAI’s runtime recovery message prints broken retry commands, and the skill promises word timestamps that anyscribe does not expose.

Reviewed HEAD `44fec4c001f7f094eebd9ad9fd5a861eb73de41a` against `b3cddc1`. This is the right PR for the requested skill and CLI audit. After corrections, merge still requires passing CI on the final SHA.

Paths below are relative to `<checkout>`.

**Earlier findings**

| Prior finding | Status | Evidence |
|---|---|---|
| Correctness S1: flag placement | FIXED | `skill/SKILL.md:36` distinguishes root flags from command options; corrected examples parse. |
| Correctness S2: API-key repair command | FIXED | `references/troubleshooting.md:228,235` supplies `YOUR_KEY`, satisfying the required value argument. |
| Correctness S3: model semantics | FIXED | `references/commands.md:91,628` distinguishes the resolved model from provider overrides and onboarding settings. |
| Correctness S4: OpenAI retry | PARTLY | Troubleshooting now uses the original input and addresses saved diarization; the runtime message still fails. See S2 below. |
| Correctness S5: setup failure fields | FIXED | `SKILL.md:132` distinguishes install failures from download failures, matching `core/local_setup.py:260–287`. |
| Correctness S6: JSON-output caveat | FIXED | `references/commands.md:95,229` qualifies output for early exits, empty/resumed batches, and other stdout. |
| Correctness S7: timeout | FIXED | `SKILL.md:311` and `references/commands.md:201` acknowledge that timeout does not terminate the running worker. |
| Correctness S8: service effects | FIXED | `references/commands.md:390` and troubleshooting describe loading, automatic start, unloading, and tray effects. |
| Correctness S9: download guarantee | FIXED | `references/providers.md:199` now warns that an uncached model can download during transcription. Its new installation exclusivity claim has a separate nit below. |
| Correctness S10: batch totals | FIXED | The example has two results, one success and one failure, matching its totals. |
| Correctness S11: relative paths | FIXED | `SKILL.md:290` and `references/commands.md:254` describe resolution from the working directory, matching the implementation. |
| Fit S1: Groq guidance and error | FIXED | Provider guidance avoids quality-tier advice for diarization; the runtime error names explicit supported providers. |
| Fit S2: setup row and routing | PARTLY | Setup no longer claims to change the provider, but the replacement instructions omit saved diarization. See S1. |
| Fit S3: Sarvam translation | FIXED | `references/providers.md:160,164` states English translation, matching `mode=translate`. |
| Fit S4: JSON snippet | FIXED | All seven fenced JSON examples parse; setup streaming output is described separately. |
| Fit S5: four stale strings | FIXED | The password/key wording, language count, native OpenAI diarization wording, and quality/chunking wording were corrected. Another timestamp claim remains, described in S3. |
| Fit S6: general-purpose recommendation | FIXED | `SKILL.md:198` describes the default balanced tier and the OpenAI fallback. |
| Extra help strings | FIXED | Update, model removal/reinstallation, local teardown, and MCP provider-test wording now match their respective paths. |
| React ElevenLabs description | DECLINED-OK | Explicitly deferred by the brief to a follow-up with a frontend rebuild. |

The newly introduced documentation defects are S1 and S4 below. S2 and S3 are retained problems, not new transcription regressions.

**S1. should-fix · CONFIRMED: the new local-default recipe can still send audio to Deepgram**

Locations: `src/anyscribe/skill/SKILL.md:134`, `src/anyscribe/skill/references/providers.md:219`, and corresponding guidance in `references/commands.md:554`.

Concrete case: the user has saved `diarize: true` and a Deepgram key. They install local transcription, then follow `anyscribe config set provider local`. That sets `provider=local` and `quality=custom`, but leaves diarization enabled.

`core/resolve.py:53–62` then selects Deepgram for an ordinary transcription. Setting `quality=free` also does not override this branch. The suggested configuration check can reveal the mismatch, but the instructions provide no explanation or working persistent remedy.

This matters particularly because the skill recommends local for privacy and offline use.

Replace the routing paragraph, and align its other copies, with:

> Setup leaves provider, quality, and diarization settings unchanged. For one local transcription, pass `-p local`; local transcription does not provide speaker labels. To make local the default, explain that saved speaker diarization must be disabled and obtain approval for that setting change. Then run `anyscribe config set diarize false`, followed by `anyscribe config set provider local`. Before processing audio, confirm that `anyscribe config --json` reports `resolved.provider` as `local`. The `free` quality tier selects local only when diarization is off.

**S2. should-fix · CONFIRMED: OpenAI’s runtime recovery commands still use the wrong input**

Location: `src/anyscribe/providers/openai.py:115,117`.

Concrete case: a YouTube recording exceeds the diarization limit. The downloader stores its audio in a temporary directory. The error prints:

```text
anyscribe "<downloaded basename>" -p deepgram --diarize
```

The orchestrator subsequently removes the temporary directory. Running the suggested command searches the current directory for that basename and fails input validation. An absolute local file outside the working directory has the same basename problem.

The second suggestion, `-p openai` without `--diarize`, also fails to disable persisted `diarize: true`.

The troubleshooting document now handles both cases correctly; the runtime message does not.

Replace the two generated retry commands with:

> Retry your original URL or file path with `-p deepgram --diarize`, replacing any existing provider flag.  
> To use OpenAI without speaker labels, retry your original input with `-p openai` and omit `--diarize`. If diarization is enabled in config, first run `anyscribe config set diarize false`.

Keep the existing API-key setup instruction. Do not substitute the temporary absolute path, because cleanup removes it.

**S3. should-fix · CONFIRMED: the skill still promises per-word timestamps**

Locations:

- `src/anyscribe/skill/SKILL.md:203`
- `src/anyscribe/skill/references/providers.md:89,143,149`
- `src/anyscribe/skill/references/troubleshooting.md:166`
- `src/anyscribe/cli/onboard.py:181`

Concrete case: an agent selects ElevenLabs because the user needs word-aligned timestamps. ElevenLabs returns word timings, but `providers/elevenlabs.py:84–112` groups them into approximately 30-word segments. The returned `TranscriptResult` preserves those segments, not the individual word timings.

Deepgram’s non-diarized path likewise groups words into approximately 30-word segments at `providers/deepgram.py:177–190`. The comparison table’s “Word-level” entries therefore overstate what anyscribe delivers.

Use this explanation:

> ElevenLabs supplies word timings to anyscribe, which groups them into approximately 30-word transcript segments. anyscribe does not expose per-word timestamps.

Replace the recommendation row with:

```text
| High-accuracy transcription | **elevenlabs** | 90+ languages; segment timestamps |
```

Change both affected comparison-table cells to `Segment-level`. Change the CLI description to the already corrected web description:

```text
High accuracy, 90+ languages, segment timestamps
```

**S4. nit · CONFIRMED: local setup is not the only installation entry point**

Location: `src/anyscribe/skill/references/providers.md:199`.

The new statement that faster-whisper is installed “only by `anyscribe local setup`” is false. Local onboarding calls `run_local_setup()` in `core/onboard_headless.py:270–274`; the Web UI also exposes setup.

Replace that sentence with:

> Installation is opt-in through `anyscribe local setup`, onboarding with the local provider, or the Web UI’s local setup flow.

**Command and contract verification**

I parsed these examples through the actual Typer command tree without invoking command actions:

| Command | Result |
|---|---|
| `anyscribe transcribe --clipboard` | Parses |
| `anyscribe --debug transcribe https://example.com/audio` | Parses |
| `anyscribe local setup --model base --yes --json` | Parses |
| `anyscribe config set provider local` | Parses; routing caveat in S1 |
| `anyscribe config set quality free` | Parses; routing caveat in S1 |
| `anyscribe https://example.com/audio -p local --json --quiet` | Parses |
| `anyscribe install-service --yes --json` | Parses |
| `anyscribe uninstall-service --yes --json` | Parses |
| `anyscribe install-skill --force` | Parses |
| `anyscribe config set openai_api_key YOUR_KEY` | Parses |
| `anyscribe batch urls.txt --timeout 300 --json --quiet` | Parses |
| `anyscribe onboard --provider openai --model whisper-1 --yes --json` | Parses |
| `anyscribe onboard --provider local --local-model large-v3-turbo --yes --json` | Parses |
| `anyscribe model info distil-large-v3.5 --json` | Parses |
| `anyscribe providers test groq` | Parses |

Twenty positive examples were checked overall. Negative controls rejected root-level `--clipboard` and onboarding’s unsupported `-m`, confirming the probe distinguishes accepted and rejected options. Parsing proves syntax; execution behavior was traced separately.

The JSON comparison covered:

- Transcription’s `success/data/error` envelope and all documented result fields.
- Batch summary fields, success rows, failure rows, and totals after filtering.
- Removal’s `data.deleted` and failure envelope.
- Local setup’s status/phase-dependent fields and NDJSON events.
- Headless onboarding’s status, provider, quality, model, workspace, local state, keys, skill installation, setup result, and config path.

The revised examples match those constructors. In particular, reported model names are qualified appropriately: a resolved plan is not always the model ultimately used by a provider, and cached results need not identify one.

I compared the changed troubleshooting strings against preflight, error classification, OpenAI, and Groq source. The Groq heading matches its runtime message. The substantive remaining recovery mismatch is S2.

`model info` now uses `MODEL_REPOS[size]`. All seven supported sizes have corresponding entries, including:

```text
large-v3-turbo   dropbox-dash/faster-whisper-large-v3-turbo
distil-large-v3.5   distil-whisper/distil-large-v3.5-ct2
```

The new test asserts the actual repository identity, not a count. The old synthesized turbo repository differs from that assertion, so the test targets the original defect. I did not execute pytest or a mutation run.

The first 14 lines of `SKILL.md` retain the copyright and AGPL notice required by `test_skill_license.py`. The bundled LICENSE matches the root LICENSE byte-for-byte. The installer copies the bundled skill and references into `~/.claude/skills/anyscribe`.

Beyond wording, the diff changes model repository reporting, adds Groq’s key URL to error guidance, and derives onboarding’s model help from `MODEL_SIZES`. I found no hidden transcription control-flow change and no deleted files. `git diff --check b3cddc1 HEAD` passed.

**Pending owner checks**

None required for these corrections. The expressly deferred Deno and Python-version decisions remain outside this review and do not block its verdict. CI verification belongs to the lead, not the owner.

**Limitations and required checks**

I read the brief, audit specification, saved diff, implementer report, all five bundled skill documents, the named CLI/provider/core/web-route/script source groups, settings, workflows, CHANGELOG, BACKLOG, and the relevant installer, downloader, vault, MCP, and test files.

No files were changed or deleted. No tests, builds, installations, services, or network calls were run. The implementer’s reported test results are not independently verified evidence. Cloud-provider behavior, current pricing, comparative accuracy, and external model availability were not live-verified.

The lead should verify the exact PR SHA and its checks:

```bash
gh pr view 18 --repo rishmadaan/anyscribe --json headRefOid,statusCheckRollup
gh pr checks 18 --repo rishmadaan/anyscribe
```

Run or obtain CI evidence for these commands on the final corrected commit, with the Python job covering both 3.10 and 3.12 and installing the workflow’s development and MCP dependencies:

```bash
ruff check src tests scripts
pytest
python -m build
bash scripts/rehearse-migration.sh
python scripts/build-docs.py
git diff --exit-code -- landing/docs
python scripts/check-docs.py
npm --prefix ui ci
npm --prefix ui run lint
npm --prefix ui run build
git diff --exit-code -- src/anyscribe/web/static
```

Approval requires S1–S3 corrected and the final commit’s required CI passing.