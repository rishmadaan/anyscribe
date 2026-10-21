**NOT YET.** Two earlier accuracy fixes remain incomplete: the docs still describe planned models as actual execution results, and still promise a complete language picker for Groq. I found no new defect introduced by the round-3 changes.

Reviewed head: `396d912d9026bbf085ae6c6472a34167a1d9c73d`, against `b3cddc1`. All repository paths below are relative to `<checkout>`.

**Earlier findings**

| Earlier finding | Status | Evidence |
|---|---|---|
| Astra D1: universal noninteractive refusal | FIXED | `docs/user/commands.md:1155` now distinguishes commands that refuse from `rm` and service commands that read confirmation; service also skips confirmation with `--json`. |
| Astra D2: JSON promised where unavailable | FIXED | Landing wording is qualified; `commands.md:1302` describes doctor as human-readable. Doctor has no `--json` option. |
| Astra D3: provider checks overpromised | FIXED | Commands, providers and getting-started distinguish loading/key-presence checks from API validation, including the Groq/Sarvam web exceptions. |
| Astra D4: planned model presented as execution evidence | PARTLY | Corrected at `commands.md:600` and `:1280`, but contradictory claims remain. See D1. |
| Astra D5: Groq language list promised | PARTLY | `providers.md:151` correctly says “No bundled picker list”; three explanatory passages still promise every supported code. See D2. |
| Astra D6: skill installation on every invocation | FIXED | `commands.md:1002` qualifies this as normal command startup, consistent with the early version/help paths. |
| Astra D7: local included in cloud chunking | FIXED | `troubleshooting.md:353` separates cloud splitting from Local’s whole-file path. |
| Opus D1: cloud/local chunking | FIXED | Same evidence as Astra D7. |
| Opus D2: Groq picker | PARTLY | Same remaining contradictions as Astra D5. |
| Opus D3: ElevenLabs wording across surfaces | FIXED within this PR’s scope | Commands and getting-started now say “90+ languages”; the provider table says 92. The React wizard and backend onboarding strings remain separate work, not globally fixed. |
| Opus D4: version-check trigger omitted | FIXED | `getting-started.md:29` names `anyscribe update --check` and `anyscribe doctor`. |
| Opus D5: configuration’s “90+” wording | DECLINED-OK | The bundled list contains 92 entries, so “90+” is accurate. |
| Opus D6: zero-network wording | FIXED by source trace | README and getting-started now describe working without an internet connection after setup. This no longer promises that libraries never attempt network access. Disconnected execution was not tested. |

The timeout example was removed and the skill-install sentences shortened as advised. Keeping exact **bundled** language counts is justified. Deferring the React wizard card is acceptable for this docs-only PR, but its stale wording remains visible in this checkout; I did not verify a follow-up PR.

**Remaining findings**

**D1. should-fix | CONFIRMED | Planned or configured models are still described as actual execution**

Locations:

- `docs/user/commands.md:725` and `:729`
- `docs/user/providers.md:92`
- `docs/user/configuration.md:64`
- Corresponding generated pages under `landing/docs/`

Concrete failure: configure OpenAI, `quality: custom`, `output_format: timestamped`, and no model pin. `providers list` displays `gpt-transcribe`, because `_provider_rows()` selects the pin or first catalog entry. The transcription resolver instead selects `whisper-1` for timestamps.

A second traced case directly exercises the requested Deepgram check: with `language: hi-Latn`, the plan can retain `nova-3` and attach a substitution note, while `DeepgramProvider._build_params()` sends `model=nova`. The plan’s model field is therefore not proof of the model sent.

Evidence: `src/anyscribe/cli/config_cmd.py:40`, `:283`; `src/anyscribe/core/resolve.py:105`; `src/anyscribe/providers/deepgram.py:47`.

Replace the Model table row with:

> **Model:** Your configured pin for this provider, or its catalog default. A transcription can substitute another model; check the run plan and its notes.

Replace the advice at `commands.md:729` with:

> **Active is your saved provider setting.** A quality tier can override it. Use `anyscribe config` to inspect the plan selected from current defaults and any substitution notes.

Replace `providers.md:92` with:

> Run `anyscribe config` to see the provider and planned model selected from current defaults, including substitution notes. Per-run flags can change that plan.

Replace the banner claim in `configuration.md:64` with:

> the page opens with a “Next run” banner showing the plan selected from current defaults and any substitution notes,

Regenerate the corresponding HTML.

**D2. should-fix | CONFIRMED | The language-picker instructions contradict the corrected Groq table**

Locations:

- `docs/user/providers.md:471`
- `docs/user/commands.md:853`
- `docs/user/configuration.md:238`
- Corresponding generated pages under `landing/docs/`

Concrete failure: a Groq user follows the instructions to open Transcribe → Options and expects a dropdown containing every supported language. Groq has no entry in `PROVIDER_LANGUAGES`. The language route consequently returns:

```json
{"languages": [], "freeform": false}
```

The corrected comparison table acknowledges this, but the surrounding guides still promise a complete list and identify only OpenRouter as an exception.

Evidence: `src/anyscribe/providers/languages.py`; `src/anyscribe/web/routes/config.py:170`.

Replace the picker explanation in `providers.md` with:

> Open Transcribe → Options to choose a language. The picker shows anyscribe’s bundled suggestions where available; these are not an exhaustive list of current provider support. Groq currently has no bundled suggestions. To specify a Groq language explicitly, use `anyscribe "<url>" -p groq --language en`, replacing `en` as needed. OpenRouter uses free-text input.

Replace the complete-list claims in commands and configuration with:

> The language input shows bundled suggestions where available. Groq currently has no bundled suggestions; OpenRouter uses free text. See “Picking a language” in the Providers guide.

Regenerate the corresponding HTML.

**Answers to the brief**

This is the requested job and the appropriate PR boundary. The diff changes only README, six user-guide sources, their six generated HTML pages, and the landing page. No runtime code, installation files or workflows changed; no files were deleted.

Source tracing supports the changed command examples, including explicit `transcribe --clipboard`, positional configuration values, onboarding’s `--model`, and batch `--resume`. I checked the changed flag/default descriptions and JSON examples against their option definitions and output construction. No additional mismatch emerged from those checks.

Independent list counts are:

| Bundled list | Entries |
|---|---:|
| Whisper | 100 |
| Deepgram | 89 |
| ElevenLabs | 92 |
| Sarvam | 23, comprising 22 Indian languages plus English |
| Groq | No registered list |

The installed Claude skill comes from `src/anyscribe/skill`, copied by `anyscribe install-skill` to `~/.claude/skills/anyscribe`. Editing user documentation does not update that bundle. Its separate correction work must not be counted as completed by this PR.

I read the renderer and matched three changed source/HTML passages: confirmation exceptions, provider-test limitations, and cloud/local chunking. Those spot checks pass. They do **not** establish full equality with a fresh render.

The six requested phrase searches leave only the legitimate Local “100 codes (Whisper’s list)” wording, appearing in both Markdown and generated HTML.

**Pending owner checks**

None. D1, D2, regeneration and CI verification are work for the lead, not decisions to hand back to the owner. The settled Deno and Python-version questions remain outside this review.

**Verification limits and remaining commands**

The saved patch matches the actual base-to-head diff. `git diff --check` passes, and tracked working-tree/index checks are clean.

I inspected the brief, audit, implementer report, full diff, affected documentation, the specified CLI/provider/core/route/settings sources, Python scripts, workflows, CHANGELOG and BACKLOG, plus the relevant skill-install, MCP and onboarding paths.

As required, I ran no application commands, tests, builds, installs, servers or network calls. Consequently, runtime behavior is source-traced, live provider behavior is untested, fresh-render equality is unverified, and CI on this SHA is unverified.

The lead should run these from the checkout after correcting D1 and D2:

```sh
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

Commit regenerated HTML before using the render-diff command as a cleanliness gate. The Python CI matrix covers 3.10 and 3.12; frontend CI uses Node 22.

To inspect checks for the currently reviewed SHA:

```sh
gh api --paginate repos/rishmadaan/anyscribe/commits/396d912d9026bbf085ae6c6472a34167a1d9c73d/check-runs
```

After fixes, verify CI against the replacement head SHA. Merge approval remains dependent on those checks passing.