# Lens packs for this review (from the independent-review skill's lenses.md)

## Every review

- Is this the job he asked for? (Wave 1 as listed in ask.md, nothing more, nothing missing.)
- Use it the way he and his customers will: the shipped build, installed, on their device, by their path, with no test hooks. Which copy does the device actually load? (Customers fetch `install.sh` and `install.ps1` straight from GitHub `main`; the website is `landing/index.html` served by Vercel; the dashboard is the committed `src/anyscribe/web/static` bundle.)
- Claims worded stronger than their evidence.

## Code PR

- His goals as invariants: a Mac without Homebrew either installs or ends with a clear next step; a Windows visitor can copy the full command; no screen says "ready" or "valid" when it is not; the wizard never loops silently; the finished transcript is one click away and readable; no existing behaviour on the keep-list breaks.
- Try to break each fix with concrete inputs: `curl | bash` with no sudo cached; no /dev/tty at all; winget installs ffmpeg but PATH is stale; a 429 with and without `insufficient_quota`; OpenRouter 402; a fake Groq, OpenRouter, Sarvam key; the check endpoint timing out; Escape and a reload during a download; a 409 from setup; a Windows file path for the "Read transcript" slug; a transcript title or text containing HTML, `javascript:` links, or `**` and `[` in odd places; timestamped and diarized transcripts.
- Tests that cannot fail (a check that passes with its guard removed), N/A entries hiding checks that could run, a test environment unlike the real one.
- Fixture tests must set test-owned home folders and ports, so no case silently uses real or inherited endpoints.
- The same pattern elsewhere: any other place that treats a key as valid without checking, any other `exit` in a script run by `iex`, any other raw-markdown view.
- Races, aborts, state left behind (polling timers after the wizard closes, a setup that keeps running after close).
- Security boundary: the key is sent only to its own provider over HTTPS and never logged or echoed; rendered transcript content cannot inject HTML or script; links limited to http and https.
- Docs and spec that claim more than the code does.
- CI on this exact SHA; a merge verdict is conditional on it.

## Mockup or screen

- Can every status and sentence actually be known from the data? Check against the code.
- Missing states: ffmpeg missing, check running, check refused, check unreachable, Sarvam not checked, download in progress after a reload, setup failed, a very long transcript, an empty transcript.
- Walk the customer's jobs in order: open the website on Windows and install; finish setup on a Mac with no ffmpeg; paste a Groq key with a typo; transcribe a video and read it.
- Anything hover-only; where the customer would hesitate or need to ask.
