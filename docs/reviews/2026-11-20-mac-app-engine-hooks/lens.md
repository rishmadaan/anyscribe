# Lens

## Every review
- Is this the job he asked for? (Engine hooks the approved Mac app needs; nothing more.)
- Use it the way he will: the dashboard in a browser at http://127.0.0.1:8457, the dashboard shared on his tailnet, the CLI, the MCP server, the Claude Code skill, and later the Mac app's window at http://127.0.0.1:<port>.
- Claims worded stronger than their evidence.

## Code PR
- His goals as invariants:
  1. No web page on another site can make the engine do anything (shut down, upload, transcribe, change settings or keys).
  2. Everything that works today without an Origin header (CLI, curl, MCP, tests) or from the dashboard itself (same-origin, and the Vite dev server at localhost:5173) still works; the tailnet share still works while held.
  3. Without ANYSCRIBE_APP=1 and without --watch-stdin, behaviour is exactly as before.
  4. In app mode the Claude Code skill is never installed or updated by the engine (startup or onboarding), and `anyscribe update` never runs pip or git.
  5. With --watch-stdin, the engine never outlives the app, and never loses a finished transcript doing so.
  6. /api/jobs reports only what the engine knows; the title is never parsed from message text.
- Try to break the Origin check with: `null`, an empty value, `http://127.0.0.1.evil.example`, `http://localhost.evil.example`, `http://[::1]:5173`, `HTTP://LOCALHOST`, `file://`, `chrome-extension://abc`, two Origin headers (first local, second evil, and the reverse), the same on a WebSocket upgrade, a tailnet name while not held, `https://<held name>.evil.example`, userinfo tricks like `http://evil.example@127.0.0.1`.
- Tests that cannot fail (a check that passes with its guard removed), N/A entries hiding checks that could run, a test environment unlike the real one.
- The same pattern elsewhere: any other route or server (MCP, routes mounted outside HostCheck, static files) reachable without the check?
- Races, aborts, state left behind: the stdin thread's hard exit during a vault write, during a local-engine pip install, during tailnet cleanup; a share left on the tailnet.
- Security boundary: origin, Host, redirects, WebSocket.
- Docs and spec that claim more than the code does.
