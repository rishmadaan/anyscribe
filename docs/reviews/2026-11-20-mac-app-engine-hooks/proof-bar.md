# What proof.md must show
- `pytest` and `ruff check src tests scripts` output (whole suite, as CI runs them).
- One test per item 1 to 4, each asserting what the user would see (the update message and exit code, the skill folder untouched, the job list's fields for a job with a known title, the engine process gone after stdin closes, a 403 for Origin https://evil.example and for Origin null with the server still running, 200 with no Origin and with Origin http://localhost:5173).
- Mutation tests, each seen failing with its guard removed and passing restored, quoting the failing assertion: the Origin check, the stdin watch, the app-mode skill skip.
- The stdin test runs the real `python -m anyscribe ui --watch-stdin` as a subprocess with a throwaway HOME and a free port, not an in-process call.
