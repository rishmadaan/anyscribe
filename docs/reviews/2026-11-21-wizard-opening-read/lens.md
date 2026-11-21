# Lens packs for this review (from the independent-review skill's lenses.md)

## Every review

- Is this the job he asked for? L1 only (ask.md), nothing more, nothing missing.
- Use it the way he and his customers will: the committed `src/anyscribe/web/static` bundle served by a real `anyscribe ui`, a real reload during a real setup, no test hooks for at least one walk.
- Claims worded stronger than their evidence.

## Code PR

- His goals as invariants: closing the wizard during a running download always asks first once anything in this wizard knows it runs and nothing newer contradicts it; nothing ever traps (only saving at Finish locks); a stale reply never moves the person backwards or changes their pick; no behaviour on the keep-list (spec.md rule 4) changes.
- Try to break it with orderings: the opening reply landing before mount, after mount with failing step reads, after a successful step read (running or not), after a start (in flight, refused, 409, succeeded and finished), after Back, after Workspace, after Finish; a remount of the local step; React StrictMode double effects; a reply landing while "Close setup?" is open.
- Tests that cannot fail (a check that passes with its guard removed), harness fakes unlike the real server's answers.
- The same pattern elsewhere: any other place a late reply writes state that something newer owns.
- Races, aborts, timers left behind after the wizard closes.
- CI on this exact SHA; a merge verdict is conditional on it.
