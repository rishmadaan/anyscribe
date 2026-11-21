# The owner's ask, in his words

2026-11-20: "Let's do a full end-to-end plan of building this into an Electron app and not just a CLI. CLI can be there. We can probably build a new Electron app, just like how T3 code is: if you actually go through it, it's web-first, but it's also an Electron app, and a stable version of it so that people can actually install it on their Mac first and also on their Windows PC or Linux PC. Right now, we'll only start with the Mac version."

Then, in order: "yes, go ahead with phase 0" (an experiment that packed Python, yt-dlp and ffmpeg inside a test Mac app and passed), "yes, go ahead with phase 1" (mockups of the new screens, reviewed by two models), and on the reviewed mockup: "Go with your recommendations." That last yes approves the screens as drawn (menu bar direction A) and starts phase 2, building the app.

Plan: a private page (the lead has it). Approved mockup, the binding design: the approved mockup (kept privately; its sha256 starts bcf26037) (open it in a browser or read its HTML; its "For the build" section lists the promises the screens depend on).

Phase 2 so far: 2a (engine hooks) and 2b (the shell) are built and their reviews closed GOOD TO GO (branches feat/mac-app-engine and feat/mac-app-shell, not yet merged). 2c, this work, adds the remaining screens and the app-side mechanics behind them, in two parallel slices (2c-app in desktop/, 2c-ui in ui/), both inside the approved build.
