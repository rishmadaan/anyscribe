# Declined review findings (anyscribe)

Each line: date, review, reviewer, scope, finding, reason. Never delete a line; supersede it with a dated line below.

- 2026-11-19, local-first-parakeet round 1, gpt-6.1-sol, `providers/local.py` plan() @ 87dbd2f: "an explicit supported language label (e.g. en) bypasses the audio language check, so Hindi audio labelled English reaches Parakeet". Declined by design (spec decision 6): an explicitly set language is the user's statement and is trusted on every engine; Whisper forced to `en` on Hindi audio also produces wrong text. The check exists for `auto`, the default.
- 2026-11-20, onboarding-wave1 round 1, opus fit (F2), `install.sh` Homebrew step @ 8d63221: "a fresh Homebrew on Apple Silicon is never saved to ~/.zprofile, so a new Terminal can't find brew, ffmpeg or Deno". REFUTED: Homebrew's own installer writes /etc/paths.d/homebrew when its prefix is /opt/homebrew and it has sudo (Homebrew/install install.sh lines 599-601 and 1083-1090, fetched 2026-11-20), and macOS's /etc/zprofile runs path_helper, so new Terminal windows find /opt/homebrew/bin; wave 1's W1 is what gives Homebrew sudo. Intel Macs use /usr/local/bin, already on PATH.
