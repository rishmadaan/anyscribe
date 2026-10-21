You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #19 (Bring developer docs, instruction files and BACKLOG in line with the code), branch `audit/building-docs`, head commit
198758df676f546f45e26504aae396a53a4e09a6, against main b3cddc1 (v0.16.5). Checkout to read: <checkout> (a git
worktree of <repo> at that commit). The full diff is
saved at <run-folder>/reviews/building-docs/diff-r2.patch. The audit findings this PR implements are at <run-folder>/audit/building-docs.md.
The implementer's own report is at <run-folder>/reviews/impl-building-docs-r2.md (treat its claims as claims).

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
LENS (this PR, developer docs and instruction files): CLAUDE.md and AGENTS.md are read by every future agent, so a wrong instruction there compounds. Check every file path in the new Architecture tree exists; every registration point named for "Adding a provider/downloader" exists at the cited module; the REST route list against src/anyscribe/web/routes/*.py decorators; the feature-coverage matrix rows against cli/main.py and routes/system.py; the Sarvam 28 s and Deepgram claims against providers/sargam.py and deepgram.py; languages.py comment edits change no behaviour (diff the non-comment lines). BACKLOG.md: version table rows against `git tag` list; is the shim checkbox evidence sound. _index.md: new row links resolve; rows stay newest-first. The journal entry: does it claim anything the other four PRs do not actually do (it names them); is its yt-dlp sentence accurate to the verified warning text "No supported JavaScript runtime could be found ... some formats may be missing".

YOU MAY RUN: read-only commands only (cat, grep, sed -n, git log/show/diff on
the checkout, python -c for parsing). YOU MAY NOT: run pytest, builds,
installs, servers, network calls, or anything that writes. Name any check you
could not run as an exact command so the lead can run it.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Round 2+: every earlier finding as FIXED / PARTLY / NOT FIXED / DECLINED-OK,
   one line of evidence each; then NEW defects the fixes introduced.
3. Findings, most severe first, numbered B1, B2...:
   severity (blocker / should-fix / nit, only these words); CONFIRMED (you
   reproduced or traced it) or PLAUSIBLE; where (file:line); what goes wrong,
   as a concrete scenario; the fix (exact replacement wording for docs).
4. Answers to any questions in this brief (advice, not findings).
5. Pending owner checks: things only the owner can confirm. They do not block
   the verdict.
6. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.

PRIOR ROUNDS. Round 1 reviewed d34ae8a. The fix commit is 198758d. Builder's claimed evidence: <run-folder>/reviews/impl-building-docs-r2.md (treat as claims). Round-1 findings and responses:
- Astra B1 (local setup example lacks --yes for agents): claimed FIXED in providers.md and CLAUDE.md.
- Astra B2 (migration guarantee broader than code): claimed FIXED, architecture.md migrate row reworded to the three callers.
- Astra B3 (release recovery assumes release exists): claimed FIXED, step 6 reworded.
- Astra B4 / Opus B6 (shim checkbox evidence): the lead downloaded the anyscribecli 0.15.2 wheel on 2026-10-21; entry_points.txt declares ascli, scribe, scribe-mcp; parenthetical now records this. Claimed FIXED.
- Opus B1 (journal lesson wrong): claimed FIXED with the replacement paragraph.
- Opus B2 ("fixed in five PRs", "one per area"): claimed FIXED; PR numbers added.
- Opus B3 (providers.md:92 Deepgram natively / no chunking in section): claimed FIXED.
- Opus B4 (second hardcoded nova spot in resolve.py): claimed FIXED in CLAUDE.md and languages.py comments.
- Opus B5 (Groq language gap recorded as design): claimed FIXED with gap note and BACKLOG line; no code change.
- Opus B7 (EOL date): claimed FIXED ("October 2026 (endoflife.date lists 2026-10-01)").
- Opus B8 (routes/config.py comment): claimed FIXED, comment only.
- Opus B9 (2b/2c markers): claimed FIXED.
- Opus B10 (line-number citations): claimed FIXED for the lines this PR added; audio-profile rows left, DECLINED-OK (inline literals, no symbol).
- From PR #16's fit review (I1): whats-automated.md publish list and a journal paragraph for the beaupy cap, 3.14 and the publish gates: claimed FIXED; the list describes PR #16 at commit 52ef77f (publish.yml now also renders docs, diffs landing/docs and rehearses migration). Check it against <checkout>/.github/workflows/publish.yml at that commit.
- Leftover Deepgram claims in core/resolve.py:58-59 and providers/openai.py:111-118: DECLINED for this PR, routed to PR #18 (code strings).

Check that each fix is real (read the code, probe it, try to break it with concrete inputs), and look for anything new, especially problems the fixes introduced.
