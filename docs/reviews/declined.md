# Declined review findings (anyscribe)

Each line: date, review, reviewer, scope, finding, reason. Never delete a line; supersede it with a dated line below.

- 2026-11-19, local-first-parakeet round 1, gpt-6.1-sol, `providers/local.py` plan() @ 87dbd2f: "an explicit supported language label (e.g. en) bypasses the audio language check, so Hindi audio labelled English reaches Parakeet". Declined by design (spec decision 6): an explicitly set language is the user's statement and is trusted on every engine; Whisper forced to `en` on Hindi audio also produces wrong text. The check exists for `auto`, the default.
