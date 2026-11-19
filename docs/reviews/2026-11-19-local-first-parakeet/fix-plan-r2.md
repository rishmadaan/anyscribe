# Fix plan, round 2 (lead's choices; binding where it decides)

Build spec.md section 5 ("Round 3 design") first; it is the repair for
R2C2, R2C3, R2C4, R2C5, R2F1 and the diagnosis's extra cases (pending
default lost on reload; extras lost on closing the wizard; PUT with
helpers-ready-but-weights-missing; headless onboarding writing the default
before setup). Rewrite `tests/test_local_ready.py::test_making_parakeet_the_default_queues_its_helpers`
and the config-set hint tests to the new behaviour, and say so in proof.md.

Then the rest of round 2:
- R2C1: spec.md section 5 item 7.
- R2C7: `onboard --yes` human output prints the restart notice when `restart_needed`.
- R2F2: copy only. Reason: "If your audio is Hindi, set your language to Hindi: Turbo is about 3 times more accurate on Hindi when it is told the language. Every recording is then treated as Hindi." Button: "My audio is Hindi: set language to Hindi". CLI: "Is most of your audio Hindi? Setting the language to Hindi makes Turbo about 3 times more accurate on it. (Every recording will then be treated as Hindi.)"
- R2F3: when no cloud key is set, the missing-key error and the quality-tier warning add one line: "Or transcribe free on this computer, no key needed: `anyscribe local setup --model parakeet-v3` (or Settings, then Local transcription)." Do not change the dataclass defaults.
- R2F4: "a typical" desktop becomes "our test" desktop in CHANGELOG and docs (grep all siblings).
- R2F5: the "works once it finishes downloading" sentence shows only while a download is pending; on failure: "Hindi and other languages won't work until you download Whisper Large v3 Turbo in Settings."
- R2F7: restart banner adds "Using the app icon? Quit anyscribe from its menu-bar or tray icon, then open it again."
- R2F8: on a local user's Settings, the "What runs by default" cloud rows say "add a key to use" in muted text instead of amber "needs API key".
- F9 leftover: display names in Settings' "Model" line and the "What runs by default" rows.
- Mix reason: add "Parakeet is the main one because it is about 4 times faster on English."

Proof: one entry per finding id (R2C1..R2C7, R2F1..R2F8 as applicable, plus the diagnosis's four extra cases), each with the test the diagnosis named where one exists; mutation-test `runnable` ignoring helpers, the set_value guard, choose's switch-only-when-runnable, the stale-reply guard (browser interception), and the R2C1 rules.
