You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #18 (Correct the bundled Claude Code skill against the CLI, fix stale CLI strings), branch `audit/skill-cli-text`, head commit
5298f4309011aadc66acabdba5872adce1060c26, against main b3cddc1 (v0.16.5). Checkout to read: <checkout> (a git
worktree of <repo> at that commit). The full diff is
saved at <run-folder>/reviews/skill/diff-r3.patch. The audit findings this PR implements are at <run-folder>/audit/skill.md.
The implementer's own report is at <run-folder>/reviews/impl-skill-r3.md (treat its claims as claims).

WHY IT EXISTS (the owner's ask, in his words): "Do an end-to-end audit of what
all is out of date and should be updated. Logically file the PRs. Run
independent review on those PRs. If they are good to go, merge them."
FIRST QUESTION: is this the job he asked for, and the right instrument for it?
If the brief, the goal or the spec is wrong, say so instead of reviewing around it.

MUST NEVER HAPPEN: a doc or skill file that tells a user or an agent to run a
command the code rejects; a doc that claims more than the code does; a change
that breaks CI (lint, tests, docs render check, static bundle check) or a user's
install; anything deleted that should not be; behaviour changes smuggled into a
docs PR.
SETTLED, DO NOT REOPEN: yt-dlp's JavaScript-runtime requirement (Deno) and
dropping Python 3.10 are decisions left to the owner, deliberately out of scope.
CHANGELOG.md gets its entries at release time, not in these PRs. The repo's own
docs use em dashes; that is house style, not a defect.
SOURCES: the checkout above (code is the source of truth: src/anyscribe/cli/*.py,
providers/*.py, core/*.py, web/routes/*.py, config/settings.py, scripts/*.py,
.github/workflows/*.yml); the diff; the spec; CHANGELOG.md and BACKLOG.md for
history.

LENS (Every review): Is this the job he asked for? Use it the way he will: a
user reads the doc and types the command, or Claude Code reads the skill and
runs it; which copy does his machine load (the bundled skill under
src/anyscribe/skill is what `anyscribe install-skill` copies to
~/.claude/skills/anyscribe). Claims worded stronger than their evidence.
LENS (Code PR): His goal written as invariants: every documented command, flag,
default, path, JSON field and route must match the code at this commit. Try to
break each fix with concrete inputs: for each changed command example, trace it
through the Typer app in cli/main.py and the subcommand module and say whether
it parses. Tests that cannot fail. The same pattern elsewhere: any other doc
line with the same bug the PR fixed but did not touch. Docs and spec that claim
more than the code does; spec that was wrong and got built anyway. CI on this
exact SHA: a merge verdict is conditional on it.
LENS (this PR, bundled skill plus CLI strings): the skill is what Claude Code reads, so every command, flag, path and JSON field in SKILL.md and references/*.md must parse and match the CLI at this commit; trace at least ten of the changed command examples through cli/main.py and the subcommand modules. Check the JSON envelope shapes against cli/transcribe.py, cli/batch.py, cli/rm.py, cli/local_cmd.py and core/onboard_headless.py field by field. Check the new troubleshooting error strings against core/preflight.py, core/errors.py, providers/openai.py, providers/groq.py word for word. For the code changes: does `model info` now read MODEL_REPOS correctly for every size in MODEL_SIZES; does the new test assert identity (a repo id) rather than a count; is test_skill_license.py still satisfied by SKILL.md's first 14 lines; any behaviour change beyond text.

YOU MAY RUN: read-only commands only (cat, grep, sed -n, git log/show/diff on
the checkout, python -c for parsing). YOU MAY NOT: run pytest, builds,
installs, servers, network calls, or anything that writes. Name any check you
could not run as an exact command so the lead can run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Round 2+: every earlier finding as FIXED / PARTLY / NOT FIXED / DECLINED-OK,
   one line of evidence each; then NEW defects the fixes introduced.
3. Findings, most severe first, numbered S1, S2...:
   severity (blocker / should-fix / nit, only these words); CONFIRMED (you
   reproduced or traced it) or PLAUSIBLE; where (file:line); what goes wrong,
   as a concrete scenario; the fix (exact replacement wording for docs).
4. Answers to any questions in this brief (advice, not findings).
5. Pending owner checks: things only the owner can confirm. They do not block
   the verdict.
6. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.

PRIOR ROUNDS. Round 1 reviewed 0b90724; round 2 reviewed 44fec4c and confirmed every round-1 fix. Round 2 left: Astra S1 / Opus S5 (local-default recipe ignores a saved diarize: true, which routes to Deepgram), Astra S2 / Opus S2 (OpenAI runtime recovery commands embed a temp filename and -p openai does not clear saved diarize), Astra S3 / Opus S1 (per-word timestamp claims in SKILL.md:203, providers.md:89/143/149, troubleshooting.md:166, cli/onboard.py:181), Astra S4 / Opus S4 (faster-whisper "installed only by local setup"), Opus S3 nit (Groq long-file error shows OpenAI's message; doc note), Opus S6 nit (.env older installs). Fix commit: 5298f4309011aadc66acabdba5872adce1060c26. Builder's claimed evidence: <run-folder>/reviews/impl-skill-r3.md (treat as claims). All six claimed FIXED. The groq.py reorder (code) remains a follow-up, DECLINED-OK. The React ElevenLabs blurb in ui/src remains a follow-up, DECLINED-OK.

Check that each fix is real (read the code, probe it, try to break it with concrete inputs), and look for anything new, especially problems the fixes introduced. Concrete inputs: render the OpenAI over-limit diarize error with a dummy path and confirm no filename in the retry lines; trace the new local-default recipe through core/resolve.py with diarize saved true and a Deepgram key, then with diarize false; grep the skill and src for any remaining per-word timestamp claim; parse each changed command example through cli/main.py.
