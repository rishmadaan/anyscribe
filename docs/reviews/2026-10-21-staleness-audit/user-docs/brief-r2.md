You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #17 (Fix stale user docs and landing page against the code), branch `audit/user-docs`, head commit
53b864b349880a1045f2dd83deef05dc648e238a, against main b3cddc1 (v0.16.5). Checkout to read: <checkout> (a git
worktree of <repo> at that commit). The full diff is
saved at <run-folder>/reviews/user-docs/diff-r2.patch. The audit findings this PR implements are at <run-folder>/audit/user-docs.md.
The implementer's own report is at <run-folder>/reviews/impl-user-docs-r2.md (treat its claims as claims).

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
LENS (this PR, user docs and landing): read as a semi-technical newcomer who copies commands. Trace every changed command example through cli/main.py and the subcommand modules; every JSON example against cli/transcribe.py and cli/batch.py field by field; every flag table row against the Typer option definitions (name, short form, default). Landing provider cards: check each number against src/anyscribe/providers/*.py and providers/languages.py counts (do not trust the audit's counts; count the lists). Confirm landing/docs/*.html equals a fresh render of docs/user/*.md by reading scripts/build-docs.py and spot-checking two changed paragraphs in both files. Any remaining line with the same bug class (top-level --clipboard, flat JSON shape, "no chunking", "pip install faster-whisper", "--yes required") that the PR missed in README.md, docs/user or landing.

YOU MAY RUN: read-only commands only (cat, grep, sed -n, git log/show/diff on
the checkout, python -c for parsing). YOU MAY NOT: run pytest, builds,
installs, servers, network calls, or anything that writes. Name any check you
could not run as an exact command so the lead can run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Round 2+: every earlier finding as FIXED / PARTLY / NOT FIXED / DECLINED-OK,
   one line of evidence each; then NEW defects the fixes introduced.
3. Findings, most severe first, numbered D1, D2...:
   severity (blocker / should-fix / nit, only these words); CONFIRMED (you
   reproduced or traced it) or PLAUSIBLE; where (file:line); what goes wrong,
   as a concrete scenario; the fix (exact replacement wording for docs).
4. Answers to any questions in this brief (advice, not findings).
5. Pending owner checks: things only the owner can confirm. They do not block
   the verdict.
6. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.

PRIOR ROUNDS. Round 1 reviewed e5e33ea. Fix commit: 53b864b. Builder's claimed evidence: <run-folder>/reviews/impl-user-docs-r2.md (treat as claims). All round-1 findings claimed FIXED: correctness D1 (batch timeout), D2 (stdout not guaranteed JSON), D3 (automation contract), D4 (uninstall-service effects), D5 (chunking per provider), D6 (data.model semantics), D7 (bare anyscribe, config set value), D8 (language catalogue counts), D9 (word-level timestamps), D10 (Groq diarization advice), D11 (network disclosure), D12 (recovery retry), D13 (providers test), D14 (flag defaults), D15 (skill install trigger), D16 (HOST/GUEST); fit D1 (landing card), D2 ("fallback"), D3, D4, D5 (subsumed). configuration.md:270 left as Deepgram-only and accurate (DECLINED-OK, check it). The web UI ElevenLabs blurb in src is fixed in PR #18, not here.

Check that each fix is real (read the code, probe it, try to break it with concrete inputs), and look for anything new, especially problems the fixes introduced. Concrete inputs: recount the four language lists in providers/languages.py; trace each changed command example through cli/main.py; compare each provider's chunking sentence to providers/{openai,groq,elevenlabs,deepgram,openrouter,sargam}.py and core/audio.py; confirm landing/docs/*.html equals a fresh render by reading scripts/build-docs.py and spot-checking three changed paragraphs; check the README network paragraph against core/updater.py and core/deps.py.
