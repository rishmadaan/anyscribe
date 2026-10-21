**NOT YET.** PR #17 fixes several real documentation errors, but introduces some unsupported claims and leaves others that affect copied commands and automation. Correct the findings below, regenerate the HTML, and require green CI on the final commit before merging.

Reviewed HEAD: `e5e33eaa172b4d069a900ecffc6fa99423efb2ce`, against `b3cddc1`. Paths below are relative to `<checkout>`. Findings are confirmed by source tracing, not live transcription.

1. **D1 · should-fix · CONFIRMED: `--timeout` does not let the batch move past stuck work.**  
   **Where:** `docs/user/commands.md:380`, `:405`, `:412`, `:1276`. Existing error left in scope.

   A user runs `anyscribe batch urls.txt --timeout 300` expecting the second URL to start after five minutes. In `cli/batch.py:257`, the worker runs inside a `ThreadPoolExecutor` context. When the timeout raises, leaving that context waits for the worker to finish before the failure handler runs. The batch can still stall, and the supposedly failed attempt can write a transcript.

   **Replace the timeout explanation with:** “If processing exceeds N seconds, the entry is reported as failed after the running task finishes. This does not cancel processing or impose a wall-clock limit: the batch waits before continuing, and the attempt may still write a transcript or incur API charges.” Remove the “caps each entry” and “abandons it and moves on” promises.

2. **D2 · should-fix · CONFIRMED: clean JSON stdout is not guaranteed.**  
   **Where:** `docs/user/commands.md:310`, `:1152`, `:1170`. The corrected `jq` field is right, but the surrounding guarantee is not.

   With yt-dlp older than 60 days, a YouTube transcription calls `ensure_ytdlp_current()` before downloading. That function prints update messages through a stdout `Console`, without receiving `quiet` (`core/deps.py:301`; `downloaders/youtube.py:32`). Consequently, even `--json --quiet | jq -r '.data.file'` can fail to parse.

   **Replacement:** “`--json --quiet` suppresses normal transcription progress, but startup and dependency-update paths can still print non-JSON text to stdout. In particular, automatic yt-dlp updates can break direct piping to `jq`. The example below assumes those messages are not emitted.”

3. **D3 · should-fix · CONFIRMED: the universal automation contract promises safeguards and output formats that do not exist.**  
   **Where:** `docs/user/commands.md:1148`.

   `anyscribe uninstall-service --json </dev/null` skips confirmation without `--yes`: `cli/service_cmd.py:67` explicitly treats JSON mode as sufficient. The same applies to installation. Conversely, commands including `doctor` and `providers test` have no `--json` option, and ordinary Typer usage errors are not universally JSON payloads.

   **Replacement:** “JSON output and confirmation behavior are command-specific. Use `--json` only where listed, and pass `--yes` for unattended operations where supported. Service installation and removal also skip confirmation when `--json` is supplied. Usage errors are not uniformly structured JSON.” Preserve the existing advice about environment variables.

4. **D4 · should-fix · CONFIRMED: uninstalling the service can stop the running tray and its server.**  
   **Where:** `docs/user/commands.md:963`, `:979`; `docs/user/troubleshooting.md:495`.

   Someone following the promise that removal only disables future startup can interrupt their current session. `core/service.py:72` unloads the LaunchAgent. The tray handles that termination signal by tearing down its owned server and exiting (`cli/tray_cmd.py:159`).

   **Replacement:** “This unloads and deletes the LaunchAgent. If launchd started the tray, unloading stops that tray and any server it started. A manually started tray is unaffected and must be quit separately. The anyscribe package remains installed.”

5. **D5 · should-fix · CONFIRMED: the new universal chunking statement is false.**  
   **Where:** `docs/user/commands.md:320`; `docs/user/providers.md:220`; also `providers.md:173`, `configuration.md:490`, `troubleshooting.md:347`, and `landing/index.html:1761`.

   `anyscribe /path/to/45-minute.mp3 -p openai --diarize` fails rather than splitting the recording. OpenAI diarization rejects any input for which `needs_chunking()` is true, including duration over 30 minutes (`providers/openai.py:107`; `core/audio.py:26`). Sarvam uses 28-second pieces, not 18-minute pieces (`providers/sargam.py:29`).

   **Replacement:** “Deepgram splits audio over 25 MB or 30 minutes into roughly 18-minute pieces. Speaker labels are independent in each piece. OpenAI transcription without diarization uses the same thresholds, but OpenAI diarization rejects audio above either threshold. Sarvam uses 28-second pieces.” Qualify the comparison table and landing card accordingly.

6. **D6 · should-fix · CONFIRMED: `data.model` does not reliably identify the model that ran.**  
   **Where:** `docs/user/commands.md:296`, `:1187`. The PR repeats this claim in its newly corrected JSON explanation.

   With `-p deepgram --language hi-Latn`, the plan can report `nova-3`, while the request uses `nova`. With `-p openai --diarize`, it can report `gpt-transcribe`, while the request uses `gpt-4o-transcribe-diarize`. The JSON writes `plan.model` (`cli/transcribe.py:142`); provider overrides happen separately (`providers/deepgram.py:47`, `providers/openai.py:83`). Cached responses also combine a current plan with an older transcript.

   **Replacement:** “`data.model` records the model selected by the resolver, not necessarily the model called by the provider. Provider overrides are described in `data.notes`; cached responses do not identify the original model. For local transcription this field is null.” In the scripting section, also use `data.cached` rather than the bare `cached` field name.

7. **D7 · should-fix · CONFIRMED: two copied instructions still fail to perform the promised action.**  
   **Where:** `docs/user/getting-started.md:149`; `landing/index.html:1872`.

   Bare `anyscribe` displays help because `no_args_is_help=True`; it does not prompt for a URL (`cli/main.py:40`). The landing example `anyscribe config set workspace_path` is rejected because `value` is required (`cli/config_cmd.py:186`).

   **Exact replacements:** “Or run `anyscribe transcribe` with no URL and paste it when prompted.”  
   “Change the path with `anyscribe config set workspace_path "$HOME/Documents/transcripts"`.”

8. **D8 · should-fix · CONFIRMED: language counts conflate catalog entries with languages, and some remain wrong.**  
   **Where:** `landing/index.html:1764`, `:1777`; `docs/user/providers.md:151`; `commands.md:738`; `getting-started.md:90`.

   Parsing the lists in `providers/languages.py` gives:
   
   | Catalog | Entries |
   |---|---:|
   | Whisper | 100 |
   | Deepgram | 89 |
   | ElevenLabs | 92 |
   | Sarvam | 23, including English |

   The new OpenAI “99 languages” does not match the 100-entry catalog. Deepgram’s 89 entries include regional variants and the `multi` mode, so “89 languages” is unsupported. The retained ElevenLabs “99 languages” also disagrees with its catalog.

   **Replacement labels:** “100 language codes in the bundled Whisper catalog”; “89 language and mode codes”; “92 language codes”; “22 Indian languages plus English.” Rename the comparison row to “Bundled language options” if using these counts. Do not present catalog counts as verified current upstream coverage.

9. **D9 · should-fix · CONFIRMED: word-level timestamp claims exceed anyscribe’s output.**  
   **Where:** `landing/index.html:1787`, `:1791`; `docs/user/providers.md:152`, `:236`, `:248`; `troubleshooting.md:342`.

   A user selecting ElevenLabs to obtain individual word timestamps gets approximately 30-word segments instead. ElevenLabs’ parser discards the intermediate word timings (`providers/elevenlabs.py:84`). Deepgram similarly groups words, or groups speaker turns when diarizing. The writer renders those segments.

   **Replacement:** “Timestamped segments derived from the provider’s word timings. anyscribe groups roughly 30 words per segment; Deepgram diarization groups speaker turns. Individual word timestamps are not exposed in the transcript.” Replace the landing badge with “segment timestamps”.

10. **D10 · should-fix · CONFIRMED: the Groq section still recommends ElevenLabs for speaker labels.**  
    **Where:** `docs/user/providers.md:289`.

    The instruction to use the `accuracy` tier for diarization contradicts the corrected ElevenLabs section. That tier selects ElevenLabs, whose integration does not request speaker labels.

    **Replacement:** “Groq does not provide speaker labels. For diarization, configure a Deepgram key and run `anyscribe "<url>" --provider deepgram --diarize`.”

11. **D11 · should-fix · CONFIRMED: the revised network disclosure knowingly describes only one installation path.**  
    **Where:** `README.md:16`, `:21`; `docs/user/getting-started.md:29`.

    For an editable Git installation, version checks fetch from the configured Git remote rather than asking PyPI (`core/updater.py:66`, `:236`). Packaged installations use pip’s configured index. Dependency installation also contacts package sources. “Three cases” and “Nothing else reaches out” are therefore not defensible. The implementer explicitly noticed the Git exception but retained the inaccurate wording.

    **Replacement:** “anyscribe has no analytics or telemetry. Network activity includes source downloads, transcription API requests, dependency and model installation, and update checks. Version checks use pip’s configured package index for packaged installs or the configured Git remote for editable installs. Downloads can attempt to upgrade yt-dlp when its release is over 60 days old.” Remove the exhaustive “three cases” and “nothing else” claims.

12. **D12 · should-fix · CONFIRMED: retrying the original URL does not reuse recovery audio.**  
    **Where:** `docs/user/troubleshooting.md:356`, `:364`.

    After a transcription failure, following `anyscribe "url"` downloads the source again. `core/orchestrator.py:110` creates a fresh temporary directory and calls the downloader; it does not read the recovery directory. Recovery audio is only saved on failure.

    **Replacement:** “Failed runs preserve downloaded audio for manual recovery. Re-running the original URL downloads it again. To avoid another download, transcribe the saved audio file directly; that retry is recorded as a local-file source.”

13. **D13 · should-fix · CONFIRMED: provider tests do not validate credentials or account credit.**  
    **Where:** `docs/user/troubleshooting.md:208`, `:212`; `docs/user/agents.md:92`.

    An invalid but nonempty API key passes the CLI check. `cli/config_cmd.py:330` loads the provider and checks whether a key exists; it makes no authentication request. MCP `test_provider` similarly reports key presence (`mcp/server.py:459`).

    **Replacement troubleshooting text:** “`anyscribe providers test` checks provider loading and whether a required key is present. It does not validate the key, connectivity, or account credit. A successful check does not rule out authentication or billing errors.”  
    **Replacement capability row:** “Check provider loading and API-key presence”.

14. **D14 · should-fix · CONFIRMED: effective defaults remain wrong in both transcription flag tables.**  
    **Where:** `docs/user/commands.md:165`, `:169`, `:371`, `:375`.

    With a configured model pin, omitting `--model` uses the pin rather than the provider default (`core/resolve.py:97`). With `diarize: true` in configuration, omitting `--diarize` does not disable diarization; the CLI only changes that setting when the flag is supplied.

    **Replacement default cells:**  
    `--model`: “Config pin, otherwise provider default; automatic switches may apply.”  
    `--diarize`: “From config (`false` initially).”

15. **D15 · nit · CONFIRMED: “any command” does not install the skill.**  
    **Where:** `README.md:7`; `docs/user/agents.md:32`; `landing/index.html:1486`, `:1989`.

    A newcomer verifies installation with `anyscribe --version` and reasonably expects the skill to exist. The eager version callback exits before automatic installation. Installation also requires `~/.claude/` to exist (`cli/main.py:50`, `:74`).

    **Replacement:** “When `~/.claude/` exists, normal commands such as `anyscribe ui` attempt to install or refresh the bundled Claude Code skill. `--version` and `--help` do not install it. Run `anyscribe install-skill` explicitly to install it.”

16. **D16 · nit · CONFIRMED: the first landing sample still implies semantic speaker identification.**  
    **Where:** `landing/index.html:1623`.

    The PR changes the second sample to numbered speakers but leaves `HOST` and `GUEST` in the first. The Deepgram integration produces numbered labels, not role identification. This file is within the PR’s scope despite the implementer calling the omission out of scope.

    **Exact replacements:** `HOST` → `SPEAKER 0`; `GUEST` → `SPEAKER 1`.

The job and instrument are appropriate: a documentation-only PR is the right way to align instructions with existing behavior. The audit specification needs correction where it supplied universal chunking language and unsupported language counts. Following that specification exactly does not establish correctness.

The diff contains only the expected 14 Markdown/HTML files, with no runtime changes or deleted files. `git diff --check b3cddc1 HEAD` passed. The changed clipboard examples, transcription JSON envelope, `jq` field path, onboarding `--model` spelling, and local setup command match the inspected declarations. The corrected Sarvam count of 22 plus English matches its catalog.

I inspected the brief, complete patch, audit, implementer report, README, six user guides, generated HTML changes, landing content, all named CLI/provider/core/web-route Python files, settings, build/check scripts, workflows, CHANGELOG and BACKLOG, plus the referenced downloader, writer, MCP, onboarding and installation code. The bundled skill and its references remain stale at this SHA; they are what `install-skill` copies, and their corrections belong to the designated sibling skill PR. This PR alone does not repair instructions Claude receives.

Two changed passages match their generated counterparts: the `data.model` paragraph at `landing/docs/commands.html:545` and Deepgram splitting paragraph at `landing/docs/providers.html:450`. That confirms synchronization at those locations, not full fresh-render equality.

**Pending owner checks: none.** The settled Deno and Python 3.10 decisions were not reopened.

The read-only brief prohibited tests, builds, installs, servers and network calls. I therefore did not verify live provider behavior, current external prices/free credits, browser presentation, CI status, or the implementer’s claimed mutation-test run. I did not execute application commands because startup can mutate configuration and installed skills.

The lead should run these exact checks in an appropriately prepared disposable checkout:

```bash
ruff check src tests scripts
pytest
python -m build
bash scripts/rehearse-migration.sh
npm --prefix ui ci
npm --prefix ui run lint
npm --prefix ui run build
git diff --exit-code -- src/anyscribe/web/static
python scripts/build-docs.py
git diff --exit-code -- landing/docs
python scripts/check-docs.py
```

Check CI for this reviewed SHA with:

```bash
gh run list --repo rishmadaan/anyscribe \
  --commit e5e33eaa172b4d069a900ecffc6fa99423efb2ce \
  --workflow ci.yml \
  --json databaseId,headSha,status,conclusion
```

After corrections, repeat the CI check against the new head SHA. Green CI remains necessary; the existing gates do not establish the factual accuracy of these documentation claims.