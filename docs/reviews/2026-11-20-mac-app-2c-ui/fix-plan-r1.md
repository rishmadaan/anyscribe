# Fix plan, round 1 (the lead's choices; binding where it decides)

Scope: 2c-ui only (ui/src, the checker and stub, docs). 2c-app is closed at its review cap and is not changed: everything below works with its bridge as it is at 70e911f. If a fix cannot be done without a 2c-app change, stop and say so instead of building it.

**The reload, first (C1, F1, C3, C7; F2 depends on it).** The real app reloads the dashboard to `/` every time the engine returns to running (2c-app main.js, `mainWin.loadURL(...)` in the status handler). A restart keeps the saved port, so the page's origin, and its sessionStorage and localStorage, survive that reload. Page state that must outlive a restart goes in storage before the reload can happen; nothing else changes.
- **Stub first.** Make `checks/stub.js` reload to `/` on every return to running, as main.js does (and keep the removal reload to `/`, not the current route). Re-run every scenario against it before fixing anything, and record which checks now fail: that is the evidence the old checks did not cover the real app.
- **C1/F1.** When the banner records an outage (engine stopped after running, or seen restarting, not started by this page; see F2), write `{job, at}` to sessionStorage. On load, when the status reads running and that note exists, show "Running again" (naming the job when there is one) and remove the note; Dismiss removes it too. Test across the stub's reload: the watched job's name appears after the reload.
- **C3.** Files from `onOpenFile` and drops go into sessionStorage synchronously inside the callback, before it returns (the preload acknowledges right after the callback; a write inside a React state updater is too late). The Transcribe page takes them from there after a reload, and a file leaves storage only when its transcription has been submitted and accepted. Test: job A running, file B arrives, the stub reloads; after the reload B is in Up next and is submitted when A finishes (assert B's path, not a count).
- **C7.** Keep the removal note until the result is consumed: claimed after a reload, or its card closed (OK or Close). Clear it at once on a refusal (ok false and no pieces, nothing saved). Test: the stub settles remove() just before the reload; the reloaded page still shows the result. Mutation-test the "kept until consumed" rule.

**C2.** `RemovalResult` handles a result with no pieces itself, wherever it comes from: the result's reason, Try again and Close. Allow `pieces: null` in the type. Test with the persisted `{ok:false, pieces:null, reason}` through the reload path.

**C5.** "Ready" only when the login shell was asked and found this app's command (`runsOurs`). State "on" with the shell not asked (`uses` null): the card's title is "The anyscribe command is added", followed by the status reason and "Open a new Terminal window and type `anyscribe --help` to check." The skill card's title then reads "The anyscribe command is added, but the Claude Code skill couldn't be installed", and the Settings row reads "On. The command is added; anyscribe couldn't check that Terminal finds it." with the reason. Fix check_ui.py:860, which expects the old claim.

**C6.** Each question is asked once (the owner's answer): Escape and the backdrop count as the quiet answer (Keep both; Skip for now) and mark it asked. Check `firstLaunch.mark()`'s result: on `{ok:false, reason}` the person's choice still goes ahead (a removal still runs), and the reason is shown in the card or result, so the question returning at the next launch is explained. Make the stub's mark return `{ok:true}` and be settable to fail. Test both.

**F2.** A restart this page started (Restart engine pending, or the removal note present) shows "Restarting anyscribe's engine. This usually takes a few seconds." and records no outage, so no "Running again" follows it. Automatic restarts keep the mockup's words.

**F3.** addToPath `ok: true` with a reason: show that reason in the added-but-missing card in place of the generic sentence; with no reason, "The line was added, but Terminal still can't see the command."

**F4.** After a refusal (`byHand` set): drop the "anyscribe can add this line to ~/.zprofile ..." paragraph and the standard line box; show the reason as plain text (not red), then the line box with `byHand`. Use the real 2c-app refusal wording in the stub.

**F5.** Whenever `occupant` is set and Terminal does not already use it, offer "Switch to this app's copy" (`turnOn({replace:true})`): in the offer card, with the words "Another anyscribe{version} is already at ~/.local/bin/anyscribe{via}." in place of the plain offer, and Skip for now; and in the Settings row (Off, plus the Switch link). Never say Terminal uses it when `uses` is null.

**F6.** Prefix the refusal in both places: "Removing the old launcher restarts the engine. " + the reason.

**F7.** In the app, Browse puts the picked file's path in the box and focuses it, as the browser does after its upload; it does not submit. Drop and the Dock still submit at once. Spec error, the lead's: record it in proof.md.

**F8.** "Off. anyscribe isn't in Terminal." alone; the skill clause only right after a successful turnOff in this view that removed it.

**F9.** The Removed card names only what was removed, from `pieces` (for example "Removed the old launcher and its menu bar icon." when there was no login item).

**F10.** The keeps-stopping banner: replace "Its log is in ~/.anyscribe/logs/app.log." with an "Open log folder" link (`openLogFolder()`); Copy details stays as built.

**F11.** Delete the overlay's name-and-size branch (the `dragging` object's fields, `mb()`, the second line): "Drop to transcribe" only.

**F12.** Ready card: "In Claude Code, ask it to transcribe a link." only when `claudeCode`; the "If Claude Code isn't on this Mac yet ..." line only when not.

**F13.** The wizard's Terminal step is titled "One last thing".

**F16.** With no Switch offered, the other-copy card's only button reads "OK".

**Declined (in ../declined.md):** C4, F14, and F15's remove button. Do not build them.

## proof.md
Append "## Round 1 fixes (one entry per finding)": one line per UPHELD id (C1, C2, C3, C5, C6, C7, F1 to F13, F15, F16): change | ran | saw. Mutation results for every new guard (the outage note, the queue's write before the ack, the removal note kept until consumed, the no-pieces branch, the readiness gate). Then the full checker run, with screenshots, read the changed states yourself, ui lint and build, the rebuilt bundle committed, and the browser run still pixel-identical. Commit after each finding.
