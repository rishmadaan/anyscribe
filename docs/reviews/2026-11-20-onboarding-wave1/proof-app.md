# Proof: builder APP, onboarding wave 1, round 0

Worktree `~/labs/projects/anyscribe-wt/wave1-app`, branch `feat/onboarding-wave1-app`, base `91bdc2b` (checked before editing).

Commits on the branch, one per item:

| SHA | Item |
|---|---|
| `40ebc18` | W4: say "no credit" when a prepaid account is empty, and don't retry it |
| `9045d27` | W5: check keys for real, and say what happened in plain words |
| `a46d64a` | W3 (wizard): say ffmpeg is missing instead of looping silently |
| `183bdf5` | W6: lock the setup wizard while the local download runs |
| `00dc861` | W8: "Read transcript" on the Done screen, and a formatted transcript view |
| `90119dc` | W8: note the renderer's one known limit (a link URL ends at its first ")") |

Each UI commit carries the rebuilt `src/anyscribe/web/static` for that commit.

## What was run

Final run, on `90119dc` (full output in `~/.review-runs/2026-11-20-onboarding-wave1/logs/final-checks.log`):

```
$ ruff check src tests scripts
All checks passed!
$ pytest
927 passed, 5 skipped, 134 warnings in 68.96s (0:01:08)
$ cd ui && npm ci            (ok)
$ npm run lint               (eslint ., no findings)
$ npm run build              (built)
$ git diff --exit-code -- src/anyscribe/web/static
static bundle current
$ git status
On branch feat/onboarding-wave1-app
nothing to commit, working tree clean
```

The suite before the walk was `926 passed, 6 skipped`. The difference is one test that skips without the local engines. The walk's local setup installed those engines into this worktree's venv, the same way a customer's setup would.

Live checks with obviously fake keys, against the running dashboard (`POST /api/providers/<name>/test`, saved in `w5-live-fake-keys.txt`):

```
groq        {"success":false,"checked":true,"message":"Groq refused this key. Check that you copied all of it, with no extra spaces."}
openrouter  {"success":false,"checked":true,"message":"OpenRouter refused this key. Check that you copied all of it, with no extra spaces."}
sarvam      {"success":true,"checked":false,"message":"Saved, not checked: Sarvam has no way to check a key in advance. It will be checked on your first transcript."}
openai      {"success":false,"checked":true,"message":"OpenAI refused this key. ..."}
deepgram    {"success":false,"checked":true,"message":"Deepgram refused this key. ..."}
elevenlabs  {"success":false,"checked":true,"message":"ElevenLabs refused this key. ..."}
```

No network at all: a second server ran inside `unshare -rn` (loopback only), port 8492, saved in `w5-offline-live.txt`:

```
groq {"success":false,"checked":false,"message":"Couldn't reach Groq to check the key. Check your internet connection, or continue: the key will be checked on your first transcript."}
openrouter {... "Couldn't reach OpenRouter ..."}
openai {... "Couldn't reach OpenAI ..."}
```

The OpenRouter endpoint was checked before relying on it. OpenRouter's own OpenAPI file (`https://openrouter.ai/openapi.json`, server `https://openrouter.ai/api/v1`) lists `GET /key` as `getCurrentKey`, with responses 200, 401 and 500. Called by hand:

- `GET /api/v1/key` with a fake key gave `401 {"error":{"message":"User not found.","code":401}}`.
- `GET /api/v1/key` with no key gave `401 "No cookie auth credentials found"`.
- `GET /api/v1/models` with no key gave `200`, which is why the old check passed any text.
- Groq's `GET /openai/v1/models` with a fake key gave `401 invalid_api_key`.

None of the fake keys reached the server log: `grep -c 'fake\|gsk_\|sk-or'` on `logs/server-a.log` returned 0.

## Guards mutation-tested

For each guard below, the test failed with the guard removed and passed with it restored. Raw outputs are under `~/.review-runs/2026-11-20-onboarding-wave1/`.

**W4, the no-credit branch in `classify_api_error`.**

Mutant 1 deletes the branch (`w4-mutant.txt`):
```
E   anyscribe.core.errors.RateLimitError: openai rate limited (429): {"error": {... "type": "insufficient_quota", ... "code": "insufficient_quota"}}
E   assert <class 'anyscribe.core.errors.ScribeAPIError'> is NoCreditError     (openrouter 402)
E   assert <class 'anyscribe.core.errors.RateLimitError'> is NoCreditError     (groq 429 insufficient_quota)
3 failed, 1 passed
```

Whether it retries, shown by calling through `with_retry` with the sleep patched out (`w4-mutant-callcount.txt` and `w4-restored-callcount.txt`):
```
mutant (branch removed): RateLimitError | calls: 4 | user_message: Rate limited by openai. Wait a moment and retry,
restored: NoCreditError | calls: 1 | user_message: Your OpenAI account has no credit. OpenAI is prepaid: add credit at https://platform.openai.com/settings/organization/billing and try again, or use the free option instead (...)
```

Mutant 2 is over-broad: `if status_code in (402, 429)`. A plain 429 then also says "no credit" (`w4-mutant2.txt`):
```
FAILED tests/test_errors.py::TestClassifyAPIError::test_429_returns_rate_limit
FAILED tests/test_errors.py::TestNoCredit::test_plain_429_is_still_rate_limited_and_retried
2 failed, 13 passed
```

Restored: `4 passed` (TestNoCredit), and the full file passes 15 of 15.

**W5, the key checks in `test_provider`.** Each mutant ran against `tests/test_provider_key_check.py`, whose fake `AsyncClient.get` behaves like the real endpoints (`w5-mutants.txt`):
```
=== M1 groq: no call, old 'API key is set' success
    assert {'success': T...set for groq'} == {'success': F...xtra spaces.'}
    4 failed, 4 passed
=== M2 openrouter: back to /api/v1/models
    assert {'success': T...ed this key.'} == {'success': F...xtra spaces.'}   (a fake key "accepted")
    1 failed, 7 passed
=== M3 sarvam: old green 'API key is set (no validation endpoint)'
    assert {'success': T...on endpoint)'} == {'success': T... transcript.'}
    1 failed, 7 passed
=== M4 unencodable key guard removed
    UnicodeEncodeError: 'ascii' codec can't encode character '\u200b' in position 13
    1 failed, 7 passed
=== M5 unreachable guard removed
    FAILED tests/test_provider_key_check.py::test_unreachable_provider_lets_them_continue
    1 failed, 7 passed
=== restored
8 passed
```

**W8, the http/https-only link guard in `TranscriptBody.tsx`.** There is no UI test runner in the repo, and adding one would be a new dependency. So the renderer was compiled with the repo's own `tsc`, rendered with `react-dom/server`, and checked by a 20-assertion Node script in the session scratchpad (not committed). The script covers both path separators in the slug, the title skipped once, HTML kept as text, `javascript:`, `data:` and `vbscript:` links not live, odd `*` `**` `[`, the timestamped and diarized lines, the quote, the rule, `code`, and an empty body.

With the guard mutated to `} else if (m[5]) {` (`w8-link-mutant.txt`):
```
AssertionError: ... <a href="javascript:throw new Error('React has blocked a javascript: URL ...')" ...>click</a>) <a href="data:text/html,x" ...>d</a> <a href="vbscript:x" ...>v</a>
```
React blocks only `javascript:`; `data:` and `vbscript:` became live links. With the guard restored: `render self-check: all assertions passed`.

The same self-check caught a real bug before commit. `a **b and [c] (d) and ** trailing` rendered as bold. Bold now needs no space just inside its stars, as in markdown, and the check passes.

**W3 and W6** add no Python condition. Their guards are UI states, proven by the walk below.

## Customer-use walk

Server: `HOME=~/.review-runs/2026-11-20-onboarding-wave1/home-a PATH=<venv>/bin:<nopath-bin> <venv>/bin/python -m anyscribe ui --port 8491 --no-open --local-only`. `nopath-bin` held only `uv`, `python3` and `node`, so ffmpeg was off the server's PATH (I read `/proc/<pid>/environ` to confirm). Browser: a T3 preview tab I opened myself. Screenshots are in `~/.review-runs/2026-11-20-onboarding-wave1/screens/`.

**a. Local setup with ffmpeg missing.** I clicked Let's go, then "On this computer".

- `/api/local/status` returned `ffmpeg_ok: False, "ffmpeg not found on PATH"`.
- The step showed "One more thing: ffmpeg", the S4 body, `sudo apt install ffmpeg` with a copy button, and Check again.
- "Download Parakeet v3 (745 MB)" was `disabled: true`, with "Install ffmpeg first (see above), then click Check again." under it.
- Check again with ffmpeg still missing showed "Still not found."
- I then linked `ffmpeg` and `ffprobe` into the server's PATH folder, with no restart. The API turned `ffmpeg_ok: True`. Check again made the notice go away and turned Download on (`disabled: false`), and the reason line went with it.
- Screens: `app-ffmpeg-notice-1440.png`, `-1000.png`, `-390.png`. At 390 px the page width was 384 and the dialog's scroll width equalled its client width (344).

The other half, ffmpeg going missing after setup, was walked during step b. I removed ffmpeg at 81% of the Whisper Small download. When it ended, the API showed `set_up: False, setup_error: None, setup_outcome: 'set_up'`, which is exactly the old silent case. The step showed the ffmpeg notice, and "Installed — continue" was disabled with the reason. After restoring ffmpeg I clicked Check again, then "Installed — continue", and the wizard moved on to Workspace. Screen: `app-ffmpeg-after-setup-1440.png`.

**b. Download lock, Escape, click outside, reload, 409.**

- **409 path.** On the local step I chose Whisper Base and Download was on. I started a setup from outside with `curl POST /api/local/setup`; a second curl POST got the raw `{"detail":"setup already in progress"} HTTP 409`. I then clicked Download in the wizard. It showed "Installing the local engines and downloading the model…", with "Back [disabled]" and "Setting up… [disabled]". The text "409" did not appear, and neither did "already in progress".
- **Escape and outside click.** During that download I pressed Escape, then clicked the backdrop at (110, 450); `elementFromPoint` there is the `role=presentation` backdrop. The dialog stayed open, and the header said "Skip is off until the download finishes". When the download ended, the wizard moved on by itself and "Skip for now" came back.
- **Reload.** I picked Whisper Small (460 MB) so the download would last long enough, clicked Download, and reloaded 1.2 s later. The page reopened straight on step 2 with "Downloading Whisper Small… 30.8%" and Whisper Small selected (`setup_last_model`). Download was not offered, there was no 409, and Skip stayed off. Screen: `app-download-after-reload-1440.png`.
- **Finish.** The summary read "On this computer, Model Whisper Small · ready". After Finish, `config.yaml` had `provider: local`, `local_model: small`.

**c. Cloud path with fake keys.** From Settings I clicked Run setup wizard, then Let's go, then "With a cloud service".

- **groq.** I typed `gsk_this_is_an_obviously_fake_key_0000` and pressed Next without Test key. Next showed "Checking key…", then stayed on the step. In red: "Groq refused this key. Check that you copied all of it, with no extra spaces." Next was disabled, and "Use this key anyway" was there. Clicking it went on to "Local transcription". Screens: `app-key-refused-1440.png`, `-1000.png`, `-390.png`.
- **openrouter.** I typed a fake key and pressed Next: refused in red, Next disabled. Typing one more character cleared the message and turned Next back on, so an edited key is never judged by an old check.
- **sargam.** I typed a fake key and pressed Next. It stayed on the step with the S3e message in amber (class `border-amber`, not green), Next on, and no "Use this key anyway". Next then went on. Screens: `app-key-notchecked-1440.png`, `-1000.png`, `-390.png`.
- **openai.** The key step shows "OpenAI is prepaid: add credit to your OpenAI account first, or transcripts will fail." Screen: `app-openai-prepaid-1440.png`. I closed the wizard with "Skip for now"; nothing was saved.
- **Settings Test buttons.** With fake Sarvam and Groq keys saved in the throwaway home, the provider rows showed the message under the row. Sarvam showed the S3e text with class `text-amber`. Groq showed the S3b text with class `text-red`. This was checked in the DOM only: the preview tab returned black screenshots for that page, so there is no Settings screenshot.

**d. A real transcription and the formatted view.**

- I typed `https://www.youtube.com/watch?v=jNQXAC9IVRw` and clicked Transcribe, with local Whisper Small and the clean format.
- Done card: Duration 0:19, Language en, Words 35, Provider "local · Whisper Small". "Read transcript" is the filled amber button (`href=/history/me-at-the-zoo`); "New transcription" is the outlined one.
- Clicking "Read transcript" opened `/history/me-at-the-zoo`.
- The view has no `<pre>`. The font is "DM Sans", 15px, and the text column is 70ch. The title appears in the h1 and 0 times in the body. Channel, Source and Duration show as bold labels. "youtube" is a link to `https://www.youtube.com/watch?v=jNQXAC9IVRw` with `target=_blank rel="noopener noreferrer"`. Then a rule, a small "TRANSCRIPT" heading and the paragraph.
- Screens: `app-done-1440.png`, `-1000.png`, `-390.png`; `app-history-clean-1440.png`, `-1000.png`, `-390.png`.

Timestamped format: I clicked Settings, then Output format "timestamped"; `/api/config` returned `output_format: timestamped`. I transcribed the same URL again and got "Already transcribed" with its link `href=/history/me-at-the-zoo`, built by the new slug helper. Re-transcribe wrote `me-at-the-zoo-2.md`. "Read transcript" then showed `**[0:00]**`, `[0:05]`, `[0:13]` and `[0:17]` as bold timestamps, each line its own paragraph. Screens: `app-history-timestamped-1440.png`, `-1000.png`, `-390.png`.

A hostile file I wrote into the throwaway vault (`sources/local/hostile-check.md`) rendered safely:

- The title `<img src=x onerror=alert(1)> title` showed as text in the h1 and was not repeated in the body. A `<script>` in the text and `<b>` in a quote also showed as text: 0 `img`, `script` or `b` elements on the page.
- The `javascript:` and `data:` links showed only their labels. The only live link was `https://example.com/a_(b`, a known limit noted in the code: a URL ends at its first `)`.
- With frontmatter `source: javascript:alert(...)`, the Source button was not shown.
- The diarized lines (`**Speaker 0** *[0:00:01]*: ...`) showed a bold name and an italic timestamp.
- `5 * 3 ** 2 and [brackets] **unclosed` stayed literal.
- A Windows path in backticks rendered as code.

**e. Screenshots.** All of the above, at 1440, 1000 and 390 px, for the ffmpeg notice, both key-check states, the Done screen, and the History view in both formats.

Servers and tabs: server 8491 (pid 3747774, command line read before stopping) got SIGTERM. Its port closed at once, but the process was still alive about 10 s later, so it got SIGKILL by the same pid. That slow exit is existing behaviour, not something these commits changed. The offline server on 8492 ran inside its own network namespace and was killed by its own pid. Both T3 preview tabs I opened (tab_2, tab_5) are closed. Tab_1 (port 8483) was not mine and was not touched.

## Item checklist

- **W3-wizard**
  - BUILT: before the download, read `ffmpeg_ok`; show S4 with the command for this OS (`FFMPEG_COMMANDS` moved to `ui/src/components/FfmpegNotice.tsx`, shared with `SetupBanner`) and Check again.
  - BUILT: Download stays disabled, with a visible reason, until ffmpeg is found.
  - BUILT: Windows-only S4 line ("quit anyscribe from the tray..."). In code only; this machine is Linux, so the line was not seen.
  - BUILT: after setup, the no-error, not-set-up case shows the ffmpeg notice (walked), or otherwise names the missing part: the engine needs a restart, the engine is not installed, or no model can run. The second branch was not walked; see "Not proven".
- **W4**
  - BUILT: a 429 with `insufficient_quota` (any provider) raises `NoCreditError`, not retried, with S1 (billing URL for OpenAI only).
  - BUILT: a 402 from any provider, previously the generic "rejected the request (402)", gets the same S1.
  - BUILT: ordinary 429s stay `RateLimitError` and keep retrying. No other error class changed.
  - BUILT: S2 on the web wizard's OpenAI key step and in the `anyscribe onboard` OpenAI key panel (tests drive the interactive wizard to the prompt).
- **W5**
  - BUILT: Groq gets a real call to `/openai/v1/models`.
  - BUILT: OpenRouter is checked with `/api/v1/key` (verified above).
  - BUILT: Sarvam returns `success: true, checked: false` with S3e, shown in amber in the wizard and Settings.
  - BUILT: every answer uses S3a to S3d. A key containing a character no header can carry answers S3b, not a codec error.
  - BUILT: Next checks the key when the current text has not been checked. Accepted goes on. A refusal or error answer stays, with "Use this key anyway". Unreachable or not checked shows in amber and Next goes on.
  - BUILT: kept the existing behaviour: the typed key is tested without being saved, and the key is never logged or echoed (none in the server log; no message contains it).
- **W6**
  - BUILT: Escape and outside clicks do not close the wizard while setup runs (`disableClose={saving || localRunning}`).
  - BUILT: "Skip for now" is replaced by "Skip is off until the download finishes".
  - BUILT: opening the wizard while `setup_running` jumps to the local step on that download (reload walked).
  - BUILT: a 409 from setup resumes watching and is never shown raw (walked).
- **W8**
  - BUILT: "Read transcript" (S10) is the main action on the Done card; "New transcription" is secondary.
  - BUILT: `transcriptSlug()` in `ui/src/transcript.ts` splits on `/` and `\`, used in both places.
  - BUILT: the formatted view, as React elements only (no `dangerouslySetInnerHTML`): headings, quotes, rules, paragraphs, bold, italic (diarized timestamps), code, http(s)-only links in a new tab with noopener noreferrer. The title is not shown twice. Body font, 15px, 70ch. Empty body says "This transcript has no text."
  - BUILT: "Copy text" unchanged.
  - BUILT: static bundle rebuilt and committed.
  - BUILT (extra, same rule): the History view's Source button now renders only for http(s) sources. It used to take any frontmatter `source` as its href.

## Existing tests changed

None. Tests were only added:

- `tests/test_errors.py::TestNoCredit` (4 tests)
- `tests/test_onboard_agent_cli.py`: the two prepaid-note tests
- `tests/test_provider_key_check.py` (new, 8 tests)

No existing test encoded the old Groq "API key is set" or Sarvam "no validation endpoint" messages. The one Sarvam test (`test_provider_test_route_accepts_the_sarvam_spelling`) checks the unchanged "API key not set" path.

## Spec problems found

1. **S3e says "Saved" before anything is saved.** On the wizard's key step the key is not saved until Finish (keep-list: config written once at Finish), so "Saved, not checked: ..." is slightly untrue there. It is true in Settings, which tests the saved key. I used the string verbatim, because INSTALL keys the troubleshooting docs on that exact text. If the lead wants it changed, both builders must change it together; a suggested wizard form is "Not checked: Sarvam has no way to check a key in advance. It will be checked on your first transcript."
2. **S1 says "{Provider} is prepaid" for every 402.** The spec asks for 402 to get "the same no-credit message", and I applied it to any provider's 402. For a provider that is not strictly prepaid, "is prepaid" is a small overstatement. I left it as specified.
3. **The dashboard shows `str(e)`, not `user_message`** (`web/jobs.py`). To make the no-credit words reach the dashboard and MCP, and not just the CLI, `NoCreditError`'s message is S1 itself. The cost: the raw provider body is no longer in that exception's text. The spec does not say which; flagging the choice.
4. **Same pattern elsewhere, not built (outside the spec's items):** Settings' "Set up local transcription" modal (`LocalSetupModal.tsx`) still ends silently when setup finishes with ffmpeg missing. It does lock while running. The `SetupBanner` on every page does say ffmpeg is missing.
5. These spec premises held when checked:
   - `set_up` needs ffmpeg (`core/local_setup.py:328`).
   - `run_setup` does not check ffmpeg, so the download runs and only `set_up` comes out false. The walk confirmed it: `setup_outcome: set_up` with `set_up: False`.
   - OpenRouter's `/api/v1/models` answers 200 to anyone, and `/api/v1/key` refuses fake and missing keys with 401.
   - 402 was unhandled: it fell through to the generic 4xx message.

## Not proven

- The second "missing part" sentence (ffmpeg present, setup ended without error, still not set up) was not walked. It needs an engine that cannot load or a broken model, which a real setup did not produce.
- The Windows-only S4 line and Windows path handling were not run on Windows. The slug helper was checked with a `C:\...\me-at-the-zoo.md` path in the render self-check.
- There is no committed UI unit test for the renderer: the repo has no UI test runner, and adding one would be a new dependency. The 20-assertion self-check and the hostile-file walk stand in for it.
- The S3d answer in the wizard UI was not clicked through. The endpoint was proven with no network (above) and by unit test. The wizard treats `checked: false` the same way for Sarvam, and that was walked.
