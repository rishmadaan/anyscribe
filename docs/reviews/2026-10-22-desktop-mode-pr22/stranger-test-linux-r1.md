# Stranger test: desktop mode on Linux (the Linux test machine, headless SSH), target 0382449

Tester: Claude Sonnet 5.5 following docs/user/getting-started.md, commands.md and troubleshooting.md word for word, from a clone of feat/desktop-mode installed into a venv (`pip install -e ".[tray]"`). Brief: stranger-test-linux.md (same folder as the review briefs).

Summary: install, status, open (URL on stderr), `open --port 9000` refusal, /api/health (app=anyscribe, ffmpeg true), API upload + transcribe (clean "OPENAI_API_KEY not set" failure), uninstall (exact copy, files removed, port free) all MATCH the guide. Both `.desktop` files pass `desktop-file-validate` (one cosmetic hint on Categories).

Findings:
1. Headless box: the tray crashed on `import pystray` (Xlib `Bad display name ""`), the bare `anyscribe ui --no-open` fallback served the dashboard; `desktop install` exited 0 and printed "Starts at login: yes" with no hint; `status` showed `healthy:true, tray_running:false, reason:null`; the guide has no headless/SSH entry (GNOME entry describes a hidden icon, a different failure). GUIDE WRONG by omission + CODE UNCLEAR.
2. tray.log holds a 113-line Rich traceback for the pystray import failure; the useful line is ~100 lines down.
3. uninstall returned slightly before the bare `ui` process exited (gone moments later; port free).
4. After uninstall `~/.anyscribe/tray.lock` (0 bytes) remains; the guide promises removal of desktop.json, app, login item, icons only.
5. `desktop-file-validate` hint: `Categories=AudioVideo;Utility;` has two main categories (app may appear twice in some menus).
6. `tray.pid`/`server.pid` did not exist in fallback mode (brief listed them; consistent with the docs).
7. Setup artefact only: `anyscribe` not on PATH because the venv was not activated (the guide's desktop section does not cover venvs; the real installer path puts it on PATH).

Not checked: tray at a real graphical login, app-menu entry in a desktop session, GNOME AppIndicator.
