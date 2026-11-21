# Lens

## Every review
- Is this the job he asked for? (The approved mockup's screens 3, 4, 5, 9 and 10 inside the app; the browser dashboard unchanged.)
- Use it the way he will: inside the Mac app on a Mac that has desktop mode, a uv-installed anyscribe and Claude Code; a fresh Mac with neither; and the plain browser dashboard he uses today.
- Claims worded stronger than their evidence.

## Mockup or screen
- Can every status and sentence be known from the bridge (bridge-v2.md with its amendments) and the engine? Check against the code, not the mockup alone.
- Missing states: empty, unknown, in progress, failed, refused, reloaded mid-call.
- Walk his jobs in order: first launch with the old launcher (Remove, then the result after the reload); the Terminal step for a new person and the one-time card for an existing one; Switch, Off, and the conflict; Add it for me (only after his yes); the engine stopping and coming back while he watches a job; dropping a file and choosing one with Browse.
- Wording: the mockup's words where it has them; the ~30 new sentences listed in proof.md read plainly and truthfully.
- Anything hover-only; where he would hesitate or need to ask.

## Code PR
- Invariants: (1) with no bridge, the dashboard behaves exactly as today; (2) addToPath, turnOn, turnOff and oldLauncher.remove are never called without the person's explicit click; (3) each first-launch question is asked once; (4) nothing claims success the bridge did not report.
- Tests that cannot fail; the stub bridge drifting from bridge-v2.md (and from 2c-app's real implementation on branch feat/mac-app-2c-app, read-only at ~/labs/projects/anyscribe-wt/mac-2c-app).
