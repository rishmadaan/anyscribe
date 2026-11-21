"""Does Chromium show a dragged file's name and size before the drop?

Drives a real browser drag (CDP Input.dispatchDragEvent, the same path a mouse
drag takes) over a page and records what dragenter, dragover and drop can read.
Run with /usr/bin/python3. Electron's renderer is Chromium, so the answer
carries over to the Mac app; the macOS drag source itself is not exercised.
"""

import json
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGE = """<!doctype html><body style="height:100vh"><script>
window.log = [];
for (const t of ['dragenter', 'dragover', 'drop']) addEventListener(t, (e) => {
  e.preventDefault();
  const f = e.dataTransfer.files[0];
  window.log.push({type: t, types: [...e.dataTransfer.types], files: e.dataTransfer.files.length,
                   name: f ? f.name : null, size: f ? f.size : null});
});
</script></body>"""

with tempfile.TemporaryDirectory() as d:
    clip = Path(d) / "team-sync-recording.m4a"
    clip.write_bytes(b"\0" * 4096)
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        page = b.new_page()
        page.set_content(PAGE)
        cdp = page.context.new_cdp_session(page)
        data = {"items": [], "files": [str(clip)], "dragOperationsMask": 1}
        for t in ["dragEnter", "dragOver", "drop"]:
            cdp.send("Input.dispatchDragEvent", {"type": t, "x": 100, "y": 100, "data": data})
            page.wait_for_timeout(100)
        print(json.dumps(page.evaluate("window.log"), indent=1))
        print("chromium", b.version)
        b.close()
