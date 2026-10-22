(Opus 5.5, effort high, fit reviewer, round 1, target 0b1dffb. Verdict: CONDITIONAL on I1 (warning must go to stderr), I2, I3.)

I1 blocker CONFIRMED deps.py:18,148-160: the new warning prints to stdout via rich Console, so `anyscribe URL --json --quiet` (the skill's call) and the MCP stdio server get warning text before the JSON. Fix: Console(stderr=True) as orchestrator.py does; ensure_ytdlp_current has the same leak.
I2 should-fix CONFIRMED deps.py:113-131: any node/deno accepted regardless of version; yt-dlp marks node<22 unsupported and silently degrades. Validate versions.
I3 should-fix CONFIRMED deps.py:278, journal:36: the doctor's missing row shows only the description, no command or link; journal claims the Deno page is shown. Put the URL in the description; fix the journal.
I4 should-fix CONFIRMED docs not updated: getting-started:33,72; commands.md:1089 (doctor list); README:41,53. Wording given.
I5 should-fix CONFIRMED deps.py:378,397: auto-update upgrades bare yt-dlp; yt-dlp-ejs pinned ==0.8.0 goes stale. Upgrade yt-dlp[default].
I6 should-fix PLAUSIBLE troubleshooting (user+skill) Linux fix lacks unzip; install.sh non-apt message should say Deno's installer needs unzip.
I7 nit: "would miss formats or fail" -> "may"; landing "Node 22+"; install.sh header step 3; CHANGELOG unzip/sudo clause; shorter warning.
I8 nit CONFIRMED web/routes/health.py:19 `ok: all(deps.values())` now false when the optional runtime is missing; use required only.
I9 nit: no installer test for "Node 22+ present means no Deno install" nor the decline path; test leaves _js_runtime_warned=True.
Answers: Windows path with colon safe (yt-dlp splits on first colon); node<22 warns and degrades, no error; --js-runtimes appends to default deno; doctor never offers optional deps; one warning per web-server lifetime acceptable; install.sh js_runtime_found only in &&/|| lists so errexit suspended; the Mac's live run used yt-dlp's vendored solver (no yt_dlp_ejs installed there, editable metadata still 0.16.0), so the dependency change was not exercised live: reinstall the editable package when updating the Mac.
Pending owner: how Node got onto the Linux box (nvm vs system PATH); which profile Deno's setup edits; whether a red runtime icon in Web UI Settings is acceptable.
