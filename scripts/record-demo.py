"""Record the landing page's hero demo: one real take of the real dashboard, captions drawn in-page.

Run the dashboard against a throwaway home first, so no personal history is on screen:

    mkdir -p "$DEMO/.anyscribe" "$DEMO/anyscribe"   # plus a config.yaml and .env with one provider key
    HOME="$DEMO" anyscribe ui --port 8459 --no-open --local-only

    python scripts/record-demo.py <reel-or-video-url> <slug-of-its-transcript> "$DEMO" <out-dir>

The source must not already be in that home's vault (`anyscribe rm <slug> --yes`), or the run is
answered from cache. Needs `pip install playwright` and Google Chrome. Output: <out-dir>/*.webm and
marks.json with the seconds to keep. Then:

    ffmpeg -i take.webm -ss <start> -to <end> -an -c:v libx264 -preset slow -crf 23 \
        -pix_fmt yuv420p -r 30 -movflags +faststart landing/assets/anyscribe-demo.mp4
"""
import json
import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8459"
URL, SLUG, DEMO_HOME, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
W, H = 1280, 720  # the page is zoomed 1.25x so text reads at hero size

OVERLAY = r"""
(() => {
  const boot = () => {
    if (document.getElementById('demo-card')) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://fonts.googleapis.com/css2?family=Unbounded:wght@300..700&family=Instrument+Serif:ital@0;1&family=Geist:wght@400..600&display=swap';
    document.head.appendChild(link);
    const css = document.createElement('style');
    css.textContent = `
      html { zoom: 1.25; }
      .min-h-dvh { min-height: 80dvh !important; }  /* 100dvh is not zoom-aware */
      #demo-card { position: fixed; inset: 0; z-index: 99990; background: #0E0D0B; color: #ECE8DC;
        display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 22px;
        text-align: center; opacity: 1; transition: opacity .6s ease; pointer-events: none; }
      #demo-card.off { opacity: 0; }
      #demo-card h1 { font-family: 'Unbounded', sans-serif; font-weight: 400; font-size: 46px; line-height: 1.12;
        letter-spacing: -0.035em; margin: 0; max-width: 980px; }
      #demo-card h1 i { font-family: 'Instrument Serif', serif; font-style: italic; font-weight: 400;
        font-size: 1.16em; letter-spacing: -0.01em; }
      #demo-card h1 b { font-weight: 400; color: #F5A524; }
      #demo-card p { font-family: 'Geist', sans-serif; font-size: 21px; color: #B6AE9D; margin: 0; letter-spacing: .01em; }
      #demo-card p.u { font-family: 'Geist', sans-serif; font-size: 18px; color: #F5A524; }
      #demo-cap { position: fixed; left: 50%; bottom: 40px; transform: translate(-50%, 8px); z-index: 99980;
        font-family: 'Geist', sans-serif; font-size: 21px; font-weight: 500; color: #0E0D0B; background: #F5A524;
        padding: 13px 26px; border-radius: 100px; white-space: nowrap; opacity: 0;
        transition: opacity .35s ease, transform .35s ease; pointer-events: none;
        box-shadow: 0 18px 50px -12px rgba(0,0,0,.8); }
      #demo-cap.on { opacity: 1; transform: translate(-50%, 0); }
      #demo-cur { position: fixed; left: 0; top: 0; z-index: 99999; width: 26px; height: 26px; pointer-events: none;
        transform: translate(512px, 620px); }
      #demo-cur.down svg { transform: scale(.82); }
      #demo-card:not(.off) ~ #demo-cur { opacity: 0; }
      #demo-cur { transition: opacity .3s ease; }
      #demo-cur svg { transition: transform .12s ease; transform-origin: 4px 3px; filter: drop-shadow(0 2px 4px rgba(0,0,0,.6)); }
    `;
    document.head.appendChild(css);
    const card = document.createElement('div'); card.id = 'demo-card';
    const cap = document.createElement('div'); cap.id = 'demo-cap';
    const cur = document.createElement('div'); cur.id = 'demo-cur';
    cur.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 3l15 8.2-6.6 1.7-2.6 6.4z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>';
    document.body.append(card, cap, cur);
    addEventListener('mousemove', e => { cur.style.transform = `translate(${e.clientX / 1.25 - 4}px, ${e.clientY / 1.25 - 3}px)`; }, true);
    addEventListener('mousedown', () => cur.classList.add('down'), true);
    addEventListener('mouseup', () => cur.classList.remove('down'), true);
    window.__card = html => { if (html === null) card.classList.add('off'); else { card.innerHTML = html; card.classList.remove('off'); } };
    window.__cap = text => { if (text === null) cap.classList.remove('on'); else { cap.textContent = text; cap.classList.add('on'); } };
    card.innerHTML = window.__firstCard || '';
  };
  if (document.body) boot(); else addEventListener('DOMContentLoaded', boot);
})();
"""

FIRST = "<h1>Study any reel or video <i>as</i> <b>text.</b></h1><p>anyscribe &nbsp;·&nbsp; free and open source</p>"
LAST = ("<h1><b>anyscribe</b></h1><p>Free and open source. Runs on your own computer.</p>"
        "<p class='u'>anyscribe.vercel.app</p>")

shutil.rmtree(out, ignore_errors=True)
out.mkdir(parents=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    ctx = browser.new_context(
        viewport={"width": W, "height": H}, color_scheme="dark",
        record_video_dir=str(out), record_video_size={"width": 1280, "height": 720},
        permissions=["clipboard-read", "clipboard-write"],
    )
    ctx.add_init_script(f"window.__firstCard = {json.dumps(FIRST)};" + OVERLAY)
    pg = ctx.new_page()
    t0 = time.time()
    now = lambda: time.time() - t0  # noqa: E731
    pause = pg.wait_for_timeout

    def cap(text):
        pg.evaluate("t => window.__cap(t)", text)

    def tidy():
        # the demo runs from a throwaway home; show the path a real install uses (~/anyscribe/...)
        pg.evaluate(
            """home => { const w = document.createTreeWalker(document.getElementById('root'), NodeFilter.SHOW_TEXT);
                 for (let n; (n = w.nextNode());) if (n.nodeValue.includes(home)) n.nodeValue = n.nodeValue.replaceAll(home, '~'); }""",
            DEMO_HOME,
        )

    def glide(locator, steps=28):
        box = locator.bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        pg.mouse.move(x, y, steps=steps)
        pause(250)
        return x, y

    pg.goto(BASE + "/", wait_until="networkidle")
    pg.evaluate("document.fonts.ready")
    pause(900)
    start = now()            # everything before this is page load: trimmed away
    pause(3200)
    pg.evaluate("window.__card(null)")
    pause(900)

    # 1. paste the link
    cap("Paste a reel or YouTube link")
    box = pg.locator("input[placeholder^='Paste a URL']")
    glide(box)
    box.click()
    pg.keyboard.type(URL, delay=16)
    pause(900)

    # 2. transcribe, live
    btn = pg.get_by_role("button", name="Transcribe", exact=True)
    glide(btn, steps=18)
    btn.click()
    run0 = now()
    cap("It fetches the audio and transcribes it")
    pg.get_by_text("Done", exact=True).wait_for(timeout=120_000)
    took = now() - run0
    tidy()
    dur = pg.locator("text=Duration").locator("xpath=following-sibling::div").inner_text()
    mins, secs = dur.split(":")
    length = f"{int(secs)}-second" if mins == "0" else f"{dur}"
    cap(f"A {length} reel, ready in {round(took)} seconds")
    pause(3600)

    # 3. history
    cap("Everything you study, kept in one place")
    hist = pg.get_by_role("link", name="History")
    glide(hist)
    hist.click()
    pause(3400)

    # 4. the transcript
    row = pg.get_by_text("Video by", exact=False).first
    glide(row)
    row.click()
    pause(1100)
    tidy()
    cap("The full script, with timestamps")
    pg.mouse.move(760, 420, steps=14)
    pause(1600)
    for _ in range(40):
        pg.mouse.wheel(0, 8)
        pause(70)
    tidy()
    pause(1500)
    cap("Saved as plain text files on your own computer")
    pause(3300)

    # 5. take it anywhere
    for _ in range(24):
        pg.mouse.wheel(0, -18)
        pause(30)
    copy = pg.get_by_role("button", name="Copy text")
    glide(copy)
    copy.click()
    cap("Copy it into your notes, or hand it to your AI")
    pause(3400)

    # 6. end card
    cap(None)
    pg.evaluate("h => window.__card(h)", LAST)
    pause(4600)
    end = now()

    ctx.close()
    browser.close()

video = next(out.glob("*.webm"))
marks = {"video": str(video), "start": round(start, 2), "end": round(end, 2), "took": round(took, 1), "dur": dur}
(out / "marks.json").write_text(json.dumps(marks))
print(marks)
