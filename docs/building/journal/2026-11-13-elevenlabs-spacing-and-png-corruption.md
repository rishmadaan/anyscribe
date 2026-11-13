---
type: troubleshooting
tags: [providers, elevenlabs, web-ui, gitattributes, landing]
tldr: "ElevenLabs spacing tokens tripled every space and halved segment length; a ui/ line-ending rule had corrupted every shipped PNG since 0.16.0; landing hero now carries a recorded demo."
---

# ElevenLabs spacing tokens, corrupted PNGs, and the hero demo

## ElevenLabs: three spaces between words

ElevenLabs returns `words` as a list of tokens typed `word`, `spacing` or
`audio_event`. The gaps between words arrive as their own tokens
(`{"text": " ", "type": "spacing"}`). `_parse_response` joined every token with
a space, so each gap became three spaces, and it counted spacing tokens toward
the 30-token segment size, so a "30-word" segment held about 15 words.

Fix: drop `spacing` tokens before grouping (`providers/elevenlabs.py`).
`audio_event` tokens such as `[bell dings]` stay. The old test fixture had no
`type` field and no spacing tokens, which is why it never caught this; the new
test uses the real token shape and asserts the exact segment texts. Watched it
fail on the old code first.

Not handled: languages written without spaces already got a space between
every token before this change, and still do.

## PNGs corrupted by `.gitattributes`

`ui/**/* text eol=lf` (added for the CI bundle hash) also matched
`ui/public/*.png`. When the images were added there in 45b1651 git normalised
their "line endings": every `\r\n` byte pair inside the PNG became `\n`,
including the one in the PNG signature. The next UI build copied the damaged
files into `web/static`, and every release from 0.16.0 shipped a dashboard with
a broken KraftedX logo and no footer doodles. Nothing failed: the server
returned 200 with `image/png` and the browser drew nothing.

Proof the damage was only that: for all seven files, the last good blob
(8ceb07d, `src/anyscribe/web/static/`) with `\r\n` replaced by `\n` is
byte-identical to the damaged file.

Fix: `*.png binary` (plus mp4/webm) in `.gitattributes`, the seven originals
restored from 8ceb07d into both `ui/public` and `web/static`, and
`test_shipped_pngs_are_valid_png_files` checks the PNG signature of every
shipped PNG. Watched it fail on the damaged files first.

## Hero demo video

`landing/assets/anyscribe-demo.mp4` is one real take of the real dashboard,
recorded with a Playwright script kept outside the repo (driving Chrome against
a throwaway home, so no personal history is on screen). Captions and the
pointer are drawn into the page by the script. Two things in the take are
staged: the page is zoomed 1.25x so text reads at hero size, and the scratch
home prefix in displayed paths is replaced with `~`. The "ready in N seconds"
caption is the measured time of that take.

The hero headline moved from the agent-first line to "Study any reel or video
as text" (owner's call, 2026-11-13: lead with creators studying other
creators' videos, Hindi and Hinglish included). Placing the video under the
headline pushes the install command below the fold on a laptop screen, which
reverses the earlier "CTA above the fold" choice in the hero CSS comment.
