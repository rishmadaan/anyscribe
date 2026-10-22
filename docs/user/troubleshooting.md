---
title: Troubleshooting
summary: Errors listed by the exact text anyscribe prints, each with a plain-English cause and a copy-paste fix.
read_when:
  - anyscribe printed an error and you want the fix
  - A transcript came out wrong and you don't know why
  - Something worked yesterday and doesn't today
---

# Troubleshooting

Find the error by the text you actually saw. Each entry says what it means and
what to type.

> **`scribe` and `ascli` are shorter aliases for `anyscribe`** — every fix below works typed as any of the three.

## Start here

Whatever the problem, run this first:

```bash
anyscribe doctor
```

It checks your dependencies, config, install, and whether an update is
available. If you're asking for help or filing a bug, paste its output — it
contains everything needed to diagnose the issue and no secrets.

If the question is about a *specific past run* — did it actually transcribe,
what happened to the one that failed — check the activity log instead:

```bash
anyscribe logs
```

That shows recent transcriptions plus any **recovery artifacts**: audio that was
downloaded before a run failed, kept so you don't have to download it again.

---

## Install and startup

### `command not found: anyscribe` (or `'anyscribe' is not recognized`)

anyscribe is installed, but the folder pip put it in isn't on your PATH.

**The instant workaround** — this always works, no setup:

```bash
python -m anyscribe onboard              # same as: anyscribe onboard
python -m anyscribe transcribe "<url>"   # same as: anyscribe transcribe "<url>"
```

**To fix the `anyscribe` shortcut properly**, first confirm it's installed:

```bash
python3 -m pip show anyscribe
```

Then add your Python scripts directory to PATH:

- **macOS** — add the Python framework `bin` directory to your PATH
- **Linux** — add `~/.local/bin` to your PATH
- **Windows** (PowerShell, as administrator):

  ```powershell
  # Find where pip installed the scripts:
  python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
  # Add that path permanently (replace <path> with the output above):
  [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';<path>', 'User')
  ```

  Then restart your terminal.

### "I upgraded and my API keys are gone"

anyscribe used to keep config and keys in `~/.anyscribecli/`; it now uses
`~/.anyscribe/`. Normally the move happens by itself on your first
transcription — but if the first thing you ran after upgrading created an empty
new folder (`anyscribe ui` or `anyscribe config`, say), the old keys can be stranded
in the legacy folder.

**Fix** — run the one-time migration. It never overwrites anything already in
the new folder, and it reports how many keys it moved, never the keys
themselves:

```bash
anyscribe migrate --dry-run    # preview — writes nothing at all
anyscribe migrate              # do it
```

Safe to run twice: a second run just reports there's nothing left to do.

### `anyscribe update` says up to date, but newer releases exist

Current anyscribe needs Python 3.11 or newer. On Python 3.10, pip and
`anyscribe update` stop at the last release that supported it and report it as
up to date, so nothing looks wrong.

**Fix** — check which Python you have:

```bash
python3 --version      # macOS / Linux
python --version       # Windows
```

If it says 3.10 or older, re-run the one-line installer from
[Getting Started](getting-started.md): it finds or installs Python 3.11 or
newer and installs anyscribe with it. Then run `anyscribe --version`. If it
still shows the old version, an older copy comes first on your PATH: remove it
with `python3.10 -m pip uninstall anyscribe` (Windows: `py -3.10 -m pip
uninstall anyscribe`) and open a new terminal.

### "Permission denied"

Usually the app folder is owned by root, from an install run with `sudo`.

```bash
ls -la ~/.anyscribe/                      # check the owner
sudo chown -R $(whoami) ~/.anyscribe/     # hand it back to yourself
```

### `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`

Only affects the MCP server (`anyscribe-mcp`), not the regular commands.

The MCP library released a version 2 that renamed the piece anyscribe imports.
anyscribe releases before 0.16.3 didn't ask for a specific version, so a fresh <!-- version-pin-ok -->
install pulled the new one and the two stopped fitting together.

```bash
pip install -U "anyscribe[mcp]"           # newer releases pin the range
```

Then restart whichever app hosts the server (Claude Desktop, Cursor) so it
launches the fixed one. See [Agents and MCP](agents.md) for the full setup.

---

## Input and downloads

### `no matches found` when you paste a URL

Your shell — zsh especially — is treating the `?` in the URL as a wildcard. This
happens before anyscribe ever runs.

**Fix:** wrap the URL in double quotes.

```bash
anyscribe transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

Or run `anyscribe transcribe` with no URL and paste it at the prompt, where no
quoting is needed.

### `No JavaScript runtime found` or `No supported JavaScript runtime could be found`

YouTube makes downloaders solve a small JavaScript puzzle before it hands over
the media. yt-dlp ships the puzzle-solving script, but needs a program to run
it: Deno (its default) or Node 22 or newer. Without one, YouTube downloads
warn, may miss formats, and can fail outright when YouTube changes the puzzle.

**Fix** — install Deno, then check that the "JavaScript runtime" row of `anyscribe doctor` says Found.

**macOS:**
```bash
brew install deno
anyscribe doctor
```

**Linux (Ubuntu/Debian; other distros: install unzip or 7z first):**
```bash
sudo apt install unzip
curl -fsSL https://deno.land/install.sh | sh
anyscribe doctor
```

**Windows (PowerShell):**
```powershell
winget install DenoLand.Deno
anyscribe doctor
```

If you already have Node 22 or newer, anyscribe uses it and there is nothing
to install. If you still see this warning, anyscribe could not find it: run
`node --version` in the same terminal you run anyscribe from. If that fails,
which is common when Node comes from nvm, install Deno as above. The one-line
installer from [Getting Started](getting-started.md) does all of this for you.

### `yt-dlp download failed: Video unavailable`

The video is private, deleted, age-restricted, or blocked in your region.

anyscribe auto-updates yt-dlp when it's more than 60 days old — YouTube changes
formats often and old versions break — so this is rarely a stale-tool problem.
Still:

1. Try a different video, to confirm anyscribe itself is working.
2. Update yt-dlp by hand: `pip install --upgrade "yt-dlp[default]"`
3. If it's age-restricted, yt-dlp needs browser cookies (advanced).

### Instagram: `rate-limit reached` or `login required`

The reel is behind a login wall. Point anyscribe at a browser you're already
logged into — it borrows the cookies, no password involved:

```bash
anyscribe config set instagram.browser firefox
```

Supported: `firefox`, `chrome`, `safari`, `brave`, `edge`, `chromium`,
`vivaldi`, `opera`. Firefox is the most reliable on macOS; Chrome's cookie
encryption makes extraction flakier.

Already configured a browser and still seeing this?

1. Open Instagram in that browser and confirm you're logged in.
2. Open the reel URL in that same browser and confirm you can watch it.
3. If it plays in the browser but not through anyscribe, the cookie store may be
   locked by the running browser — quit the browser and retry.

### Instagram: `private account`

The poster's account is private. Cookies from a browser logged into an account
that *follows* them will work; cookies from any other account won't.

### Instagram: `video unavailable` / `post not found`

The reel was deleted, made private, or is region-locked. Nothing to fix on your
side.

---

## Providers and API keys

### `OPENAI_API_KEY not set` (or any other missing-key error)

The key that provider needs isn't in `~/.anyscribe/.env`.

```bash
anyscribe config set openai_api_key YOUR_KEY   # set it directly
anyscribe onboard --force                       # or re-run the wizard
```

### `WARNING: quality 'X' wants Y but no Y_API_KEY is set`

Not an error — anyscribe went ahead using your configured provider instead. Your
quality tier prefers a provider whose key you don't have.

**Either add the missing key:**

```bash
anyscribe config set deepgram_api_key YOUR_KEY
```

**Or pick a tier you have a key for.** `anyscribe config` shows which keys are
present in its `Key` column.

### `Provider error` or general API failures

```bash
anyscribe providers test                          # is the key set?
anyscribe "url" --provider openai                 # does another provider work?
```

`anyscribe providers test` only checks that the provider loads and that its API
key is set. It doesn't contact the provider, so it can't tell you whether the key
is valid or the account has credit. If the test fails, the key is missing. If it
passes but transcription fails, the key may be wrong or expired, or the account
may be out of credit: check your provider's dashboard, and try another provider
to see whether it's the service or the file.

### "Next run" isn't the provider I set

`quality` outranks `provider`. If `quality` is a tier
(`accuracy`/`balanced`/`cost`/`free`), that tier picks the provider and your
`provider` line is ignored.

```bash
anyscribe config    # look at the (…) after the model — `quality: balanced` means the tier won
```

**Fix:** set the provider through the CLI, which writes `quality: custom` in the
same save — that's what makes the choice stick:

```bash
anyscribe config set provider elevenlabs
```

Hand-editing `config.yaml` is the usual cause: writing `provider:` without also
writing `quality: custom` leaves the tier in charge.

### `Unknown model 'whisper-2' for openai.`

(or, for a per-run `-m`, `Unknown model 'whisper-2' for provider 'openai'.`)

That model isn't in the provider's list. anyscribe rejects it before downloading or
spending anything, and the error names the valid options.

```bash
anyscribe config --json          # each provider's current model and alternatives
anyscribe providers list --json
```

Two cases that look like bugs but aren't:

- **`elevenlabs` and `sargam` have exactly one model each**, and `local` has
  none — its sizes come from `anyscribe model list`, not `-m`.
- **`extra_models.<provider>` is rejected for everything except `openrouter`.**
  By design: every other provider's models ship with anyscribe releases because
  each response shape needs parsing code. The fix is `anyscribe update`, not a
  config key.

### OpenRouter: `model not found` / 404

The slug you pinned isn't available on OpenRouter. OpenRouter is the one
provider anyscribe doesn't validate models for — it forwards any name unchanged —
so a typo or a retired slug only fails once the request reaches the API. Old
pins to models OpenRouter has since removed are the most common cause.

**Find the pin:**

```bash
anyscribe config --json     # resolved.model, and providers[].default_model
anyscribe config show       # provider_models.openrouter
```

**Set a current slug:**

```bash
anyscribe config set provider_models.openrouter openai/gpt-audio-mini
```

Any audio-capable OpenRouter slug works — see
[openrouter.ai/models](https://openrouter.ai/models) for what's live today.

> A leftover `OPENROUTER_MODEL=` line in `~/.anyscribe/.env` is **not** the
> cause — that variable is no longer read at all. Delete the line and use
> `provider_models.openrouter` instead.

---

## Transcription results

### "Already transcribed" — nothing got re-transcribed

Not an error. anyscribe found an existing transcript whose `source:` frontmatter
matches this URL or file, so it handed you that file back instead of
re-downloading and re-paying for it. You'll see
`Already transcribed: <path> — use --force to re-transcribe.` — in JSON that's
`"cached": true`, and in a batch the row is marked `CACHED`.

**If you genuinely want a fresh run** (you switched providers, or the source was
re-uploaded):

```bash
anyscribe "url" --force
```

**If you want the old one gone entirely:** `anyscribe rm <path-or-slug>` first,
then transcribe again.

### Transcription came out in the wrong language

Auto-detection guessed wrong.

```bash
anyscribe "url" --language en        # force it for one run (or es, fr, hi, …)
anyscribe config set language hi     # or make it the default
```

### Timestamped or diarized output came out as plain paragraphs

The model that ran doesn't return segment timestamps, so there's nothing to
build `[mm:ss]` markers from. On OpenAI that's `gpt-transcribe` (the default),
`gpt-4o-transcribe`, and `gpt-4o-mini-transcribe`; `sargam` and `openrouter`
never return them at all.

**On OpenAI this shouldn't happen on its own** — anyscribe swaps in `whisper-1`
when your output format is `timestamped` or `diarized`, and prints
`switched to whisper-1 — gpt-transcribe can't produce timestamps`. So if you got
paragraphs, one of these is true:

1. **You passed `-m`.** An explicit per-run model always wins, which suppresses
   the swap. Re-run without `-m`, or with `-m whisper-1`.
2. **The provider isn't OpenAI.** Sarvam and OpenRouter have no timestamped
   model to fall back to. Switch: `anyscribe "url" -p deepgram --force`
3. **Your `output_format` is `clean`.** There were never going to be timestamps:
   `anyscribe config set output_format timestamped`

**Check what the current defaults would select:**

```bash
anyscribe config --json     # resolved.provider, resolved.model, resolved.notes
```

This does not reconstruct a previous run or its per-run flags. Use that run's
output and notes when diagnosing it.

To force Whisper on every OpenAI run:
`anyscribe config set provider_models.openai whisper-1`. Deepgram and ElevenLabs
also give timestamps, in segments of about 30 words; anyscribe doesn't show a
time for every word.

### A long video is taking forever

With cloud providers, anything over 30 minutes (or 25 MB) is split into pieces
and transcribed piece by piece, then merged. That's normal, not a hang. (Sarvam
always works in 28-second pieces. OpenAI with `--diarize` doesn't split: it
refuses files that long, so use Deepgram for long recordings with speakers. The
local provider doesn't split at all; it works through the whole file in one go.)

**Rough guide:** cloud providers run at roughly real-time speed. Local
transcription on CPU ranges from about real time (`large-v3`) to about 10× faster
than real time (`tiny`); the usual `base` runs about 7× faster.

### Audio left over after a failed run

When a transcription fails *after* the audio downloaded, anyscribe keeps that audio
rather than throwing it away, so you can retry without downloading it again.

```bash
anyscribe logs
```

Recovery artifacts appear in their own section, separate from the activity log.
To retry without downloading again, transcribe the saved file directly. It lives
in `~/.anyscribe/recovery/`, under the name `anyscribe logs` shows:
`anyscribe "$HOME/.anyscribe/recovery/<name>"`. The new transcript then lists the
source as a local file rather than the original URL. Re-running `anyscribe "url"`
also works, but downloads the source again (add `--force` if it partly wrote a
transcript). Or just delete the file if you've moved on — nothing else references it.

---

## Local (offline) transcription

### `faster-whisper is not installed`

The local provider is opt-in and needs a one-time install:

```bash
anyscribe local setup --model base
```

That installs faster-whisper into the same Python environment as anyscribe and
downloads the model. The first download needs internet (~150 MB for `base`);
everything after that is fully offline.

> `--model` is deliberately required — anyscribe will never pick a model size for
> you. `base` is the recommended starting point.

### Checking what's actually installed

```bash
anyscribe local status
```

Reports faster-whisper's version, whether ffmpeg is present, which models are
cached, disk usage, and how anyscribe was installed. It always exits 0, so it's
safe to run before setup.

### Model weights look corrupted

Delete and re-download in one step:

```bash
anyscribe model reinstall base --yes
```

---

## Web UI, tray and desktop app

### The "Setup needed to start transcribing" banner won't go away

The banner appears when either of two things is missing, and it disappears on
its own — it re-checks every 30 seconds — once both are satisfied:

1. **ffmpeg (and ffprobe) aren't installed.** The banner shows the exact install
   command for your platform, with a copy button.
2. **No transcription provider is set up at all.** Add an API key under
   **Settings → Providers**.

> **Using local transcription only?** That counts. Once faster-whisper is
> installed (`anyscribe local setup --model base`, or the **Set up local
> transcription** button on the Local provider card in Settings), the provider
> requirement is satisfied without any API key.

You can also dismiss the banner with the ✕ for the current session.

### The Remove key button is missing for a provider

That provider's key is coming from your shell environment — an
`export OPENAI_API_KEY=…` in your shell profile, say — not from
`~/.anyscribe/.env`. anyscribe can't edit your shell config, so it hides a button
that wouldn't work. Unset it where you set it.

### `The tray companion needs extra packages` / the tray won't start

The tray needs the optional `[tray]` extra (`pystray`, `Pillow`, and `pyobjc` on
macOS). The one-line installers include it by default — if you see this message,
you almost certainly installed with a bare `pip install anyscribe`:

```bash
pip install -U "anyscribe[tray]"
anyscribe tray
```

### The tray is running but there's no icon in the menu bar

If the server answers at `http://127.0.0.1:8457` but you can't find the waveform
icon, check whether a menu-bar manager is running — Hidden Bar, Bartender, Ice,
Dozer. macOS inserts new status items at the **left** of the strip, which these
apps hide by default. Expand the manager (its chevron) and drag the anyscribe
waveform to the always-visible side.

> Very old versions had a bug where the icon never appeared at all — fixed in
> 0.13.2. Run `anyscribe update` if you're on anything older. <!-- version-pin-ok -->

### `An anyscribe tray is already running.`

A tray is already active and its pidfile (`~/.anyscribe/tray.pid`) still points
at a live process. This is intentional — anyscribe refuses to start a second tray
rather than collide with the first.

**Fix:** use the existing one (check your menu bar or system tray), or quit it
first (menu → Quit, or Ctrl+C in its terminal) and relaunch. This isn't an error:
the second `anyscribe tray` exits successfully, so a login item that runs it
again doesn't keep retrying.

### `The tray isn't installed. Run: pip install "anyscribe[tray]" first.`

You'll see this from the **Settings → Startup → Start at login** toggle,
`anyscribe install-service`, or `anyscribe desktop install`. All three refuse to
set up a login item that couldn't run, because the tray's extra packages are
missing — usually because anyscribe was installed with a bare
`pip install anyscribe`. Add them, then try again:

```bash
pip install "anyscribe[tray]"
anyscribe desktop install
```

### Transcribing from the app says ffmpeg (or Deno) is missing, but the terminal works

When anyscribe starts at login or from the app icon, it doesn't get your
terminal's settings. In particular it doesn't get your *PATH* (the list of
folders your computer searches for programs like ffmpeg). Desktop mode saves a
copy of your PATH when you install it, plus the usual Homebrew and Deno folders.
If you installed or moved ffmpeg or Deno afterwards, that saved copy can't find
it, while `anyscribe` in a terminal still can.

**Fix:** run the install again. It saves your current PATH and restarts
anyscribe:

```bash
anyscribe desktop install
```

### The desktop app stopped opening after I reinstalled or upgraded Python

The app and login item remember the exact Python that ran
`anyscribe desktop install`. If that Python is removed or replaced, they point
at nothing. Check:

```bash
anyscribe desktop status
```

It shows `Healthy: no` with the reason, e.g. `The recorded Python (...) no longer
exists. Run: anyscribe desktop install`. Run that command; it points everything
at your current Python. Do the same once after `pip install --upgrade anyscribe`.

### Clicking the app does nothing (Windows)

On Windows the app runs without a console window, so it has nowhere to show an
error. It writes it to `~/.anyscribe/logs/tray.log` instead
(`%USERPROFILE%\.anyscribe\logs\tray.log`). Open that file and read the last
lines and look for lines starting with `desktop open:` (the file also holds the
tray's and the server's own output). The most common one is
`Port 8457 is in use by another program.`, fixed by
`anyscribe desktop install --port 9000` (any free port).

### No tray icon on Linux (GNOME)

Plain GNOME (Fedora Workstation and Debian, for example; Ubuntu ships the fix
already) hides tray icons unless the **AppIndicator** extension is installed. anyscribe is still running; you just
can't see its icon. Open the dashboard with the **anyscribe** icon in your app
menu (or `anyscribe desktop open`). To get the icon and its **Quit** menu back,
install your distribution's AppIndicator extension
(`gnome-shell-extension-appindicator` on Fedora and Debian). On Fedora and Debian
you may also need to switch it on in the **Extensions** app. Then log out and
back in. To stop anyscribe without the icon: `anyscribe desktop uninstall`.

### Windows didn't show a security warning when I installed

That's expected. Windows' SmartScreen warning (and macOS's Gatekeeper prompt) is
for apps downloaded through a web browser. Desktop mode doesn't download an app:
it builds the small launcher on your own machine from the anyscribe you just
installed, so there is nothing for those checks to flag.

### `port already in use`

**`anyscribe ui` handles this itself.** If the port is taken it looks at the next
ten, starts on the first free one, and tells you which:

```
Port 8457 busy — using 8458.
```

Nothing to do. You only see an error if all eleven are busy, and only then do you
need to name a port yourself:

```bash
anyscribe ui --port 9000
```

**`anyscribe tray` behaves differently, on purpose.** If an `anyscribe ui` server is
already listening on its port, the tray **attaches** to that server instead of
starting a second one — that's expected, not a bug. The tray doesn't roll forward
to another port (it would then be pointing at a server nothing else knows about),
so if an unrelated process holds the port, give the tray a different one:

```bash
anyscribe tray --port 9000
```

### Removing the tray completely

```bash
anyscribe desktop uninstall
```

This stops the tray and its server, then removes the app icon, the login item and
the icons, on macOS, Windows and Linux. Your transcripts, config and API keys stay.
Optionally drop the extra packages afterwards: `pip uninstall pystray Pillow`.

Only turned on start-at-login, never the app? `anyscribe uninstall-service --yes`
removes the login item. It never stops a tray that is already running; quit that
from its menu (menu → Quit). anyscribe itself stays installed either way.

---

## Last resort

### Config or workspace looks corrupted

```bash
anyscribe doctor     # find out what's actually wrong first
```

The nuclear option resets your config and API keys. **Your transcripts are
safe** — they live separately in `~/anyscribe/`:

```bash
rm -rf ~/.anyscribe
anyscribe onboard
```

> Check `anyscribe config show` first if you set a custom workspace path, and back
> up that folder if the transcripts matter to you.

---

## Still stuck?

Run `anyscribe doctor` and include its full output when you
[open an issue](https://github.com/rishmadaan/anyscribe/issues). It covers
dependencies, config, install type, and version — everything needed to reproduce
your setup, and nothing sensitive.
