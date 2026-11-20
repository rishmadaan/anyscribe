You are an independent reviewer. This is an approved, read-only review: do not
ask for consent. Delete nothing, edit nothing, send nothing, start or stop
nothing. Write no file; put the whole report in your final message. Skip any
repo startup routine; read only what this brief names. Test folders, leave
them alone: ~/labs/projects/anyscribe-wt/wave1/tests.

THE PACKET, read all of it first: ~/labs/projects/anyscribe-wt/wave1/docs/reviews/2026-11-20-onboarding-wave1/
ask.md (the owner's ask, in his words; the first question is whether this is
the job he asked for and the right instrument for it; if the brief, the goal or
the spec is wrong, say so instead of reviewing around it), spec.md, target.md,
proof.md plus proof-install.md and proof-app.md (what the builders ran and saw:
claims to check, not facts), lens.md;
~/labs/projects/anyscribe-wt/wave1/docs/reviews/declined.md (SETTLED, DO NOT REOPEN).

THE TARGET: repo checkout ~/labs/projects/anyscribe-wt/wave1, branch
feat/onboarding-wave1 at commit 8d63221 (GitHub PR rishmadaan/anyscribe#26).
The change under review is `git -C ~/labs/projects/anyscribe-wt/wave1 diff 7ab1539..8d63221`
(7ab1539 is main, v0.19.0). The generated files `src/anyscribe/web/static/**`
and `landing/docs/**` are built from `ui/` and `docs/user/`; review the sources.

YOUR ROLE: fit. Is this what he asked for (wave 1 exactly as approved, nothing missing, nothing extra), does it read right to its reader (a non-technical creator who has never opened a terminal: read every new user-facing sentence and the builders' screenshots as that person), is it the simplest thing, what would he object to.

MUST NEVER HAPPEN:
- A customer's install stops silently, or the Windows window closes and takes the error with it.
- Any screen or box says ready, valid, accepted or set up when it is not.
- A customer's API key is logged, echoed, stored before Finish, or sent anywhere but its own provider over HTTPS.
- Transcript content (titles, text, links from the internet) runs as HTML or script, or produces a live non-http(s) link.
- An ordinary rate limit (429 without insufficient_quota) stops being retried.
- The setup wizard loops silently or can be closed mid-download and lose state.
- Anything on spec.md's keep-list breaks, or the tailnet code and the web app's Host check change.

BUDGET: this is round 1 of at most 3; about 30 minutes.

SOURCES beyond the packet: the files the diff touches, their callers, and
`src/anyscribe/vault/writer.py` (the markdown shapes the new renderer must
handle). Screenshots from the builders' walks are in
~/.review-runs/2026-11-20-onboarding-wave1/screens/ (app-*.png,
install-*.png) and raw run outputs in that folder's logs/, install-logs/ and
w*-*.txt files.

LEAD-MADE CHANGES: commit 8d63221 rewords the Sarvam key message from
"Saved, not checked" to "Not checked yet" in 10 files (code, its test, docs,
regenerated landing/docs) and adds proof.md and review-log.md. Read these
first: the lead cannot see its own blind spot.

LENS: ~/labs/projects/anyscribe-wt/wave1/docs/reviews/2026-11-20-onboarding-wave1/lens.md
(all three packs: Every review, Code PR, Mockup or screen).

YOU MAY RUN: read-only commands: git log/show/diff/grep on that checkout,
grep, sed -n, cat, `bash -n` on the scripts. YOU MAY NOT: run tests, builds,
servers, installers, Docker, package installs, anything that writes; push,
comment on the PR, or call any provider API.

REPORT
1. Verdict first: GOOD TO GO / NOT YET / CONDITIONAL on <what>.
2. Findings, most severe first, numbered F1, F2...: severity
   (blocker / should-fix / nit, only these words); CONFIRMED (you reproduced
   or traced it) or PLAUSIBLE (you did not; say what would settle it); where
   (file:line); what goes wrong, as a concrete scenario; the fix.
3. Answers to any questions in this brief (advice, not findings).
4. Pending owner checks: things only the owner can confirm.
5. What you could not check, and why; any check you could not run, as the
   exact command. What you inspected.
If you find nothing, say so clearly and name what you inspected. No em dashes.
