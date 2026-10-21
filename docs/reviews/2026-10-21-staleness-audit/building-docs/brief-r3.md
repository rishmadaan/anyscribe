You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Put the whole report in your final message. Test folders, leave them
alone: tests/, .cache/, ui/node_modules/. Skip any repo startup routine; read
only what this brief names.

WHAT: anyscribe pull request #19 (Bring developer docs, instruction files and BACKLOG in line with the code), branch `audit/building-docs`, head commit
5ed32bdf266680e90d4270bf1a61ae47f12e60c1, against main b3cddc1 (v0.16.5). Checkout to read: <checkout> (a git
worktree of <repo> at that commit). The full diff is
saved at <run-folder>/reviews/building-docs/diff-r3.patch. The audit findings this PR implements are at <run-folder>/audit/building-docs.md.
The implementer's own report is at <run-folder>/reviews/impl-building-docs-r3.md (treat its claims as claims).

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

PRIOR ROUNDS. Round 1 reviewed d34ae8a; round 2 reviewed 198758d and confirmed every round-1 fix. Round 2 left: Astra B1 should-fix (publish intro "any failure stops the release before PyPI" overclaims; step 9 runs after upload), Astra B2 (downloaders.md step 3 never adds to DOWNLOADERS), Astra B3 (whats-automated "no automatic updates" false for yt-dlp), Astra B4 nit (release example uses the existing tag 0.5.0), Opus B1 (merge order: #16 before #19; no text change), Opus B2 (same as Astra B1), Opus B3 nit (providers.md:92 refusal is size OR duration), Opus B4 nit (model download is not a separate required step), Opus B5 nit (release-checklist step 6 lost the create command; troubleshooting row points at the post-publish step), Opus B6 nit (Key Technical Decisions auto-migration bullet lists three), Opus B7 nit (journal "same gates as CI"; publish runs on 3.12 only). Fix commits: 4ff970e and 5ed32bdf266680e90d4270bf1a61ae47f12e60c1. Builder's claimed evidence: <run-folder>/reviews/impl-building-docs-r3.md (treat as claims). All claimed FIXED; Opus B1 is a merge-order condition the lead will honour (#16 merges first).

Check that each fix is real (read the code, probe it, try to break it with concrete inputs), and look for anything new, especially problems the fixes introduced. Concrete inputs: the 9-step publish list against <checkout>/.github/workflows/publish.yml at e4fd070 (PR #16's current head); ensure_ytdlp_current callers; release.sh's tag-exists check; the release-checklist step numbering end to end.
