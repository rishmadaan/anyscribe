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

**Just ran the one-line installer?** Open a new terminal window first. The
window you installed from may not know the new folder yet; when that's the
case, the installer's last box says so and prints the full path that works in
that window.

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

### "Homebrew didn't finish installing, so anyscribe can't continue."

The full message ends: "Install Homebrew from https://brew.sh (copy its one
line into Terminal), then run this anyscribe installer again."

On a Mac, the installer uses Homebrew (the standard tool for installing
programs from Terminal) to bring in Python and ffmpeg. You said yes to
installing it, but Homebrew stopped before it finished. The usual reasons: the
password was mistyped or the prompt was cancelled, your Mac account isn't an
Administrator, the internet dropped, or you pressed a key other than Return
when Homebrew asked to continue.

**Fix:**

1. Open [brew.sh](https://brew.sh), copy the one line under "Install
   Homebrew", paste it into Terminal and press Return. It asks for your Mac
   password (nothing shows while you type) and can take 10 to 20 minutes.
2. When it finishes it prints **Next steps** with two or three lines to copy:
   run those too, so Terminal can find Homebrew next time.
3. Run the anyscribe install line again.

### "anyscribe is installed, but can't transcribe yet" (installer) or "One more thing: ffmpeg" (setup wizard)

Both mean the same thing: **ffmpeg**, a free audio tool anyscribe needs to read
audio and video, isn't installed (or the program can't find it). anyscribe
itself installed fine. The installer's box ends with the command for your
computer, and the setup wizard shows it with a copy button:

| Your computer | Command |
|---|---|
| Mac | `brew install ffmpeg` |
| Windows (PowerShell) | `winget install Gyan.FFmpeg` |
| Linux (Ubuntu, Debian) | `sudo apt install ffmpeg` (Fedora: `sudo dnf install ffmpeg`, Arch: `sudo pacman -S ffmpeg`) |

On a Mac or Linux, run it in a terminal, then click **Check again** in the
wizard. The wizard keeps the download button off until ffmpeg is found, so the
local setup can't start without it.

- **Windows:** the anyscribe that is already running doesn't see programs
  installed after it started, so **Check again** can't find a new install.
  After running the command, quit anyscribe from the tray (the icon near the
  clock) and open it again from the Start menu. Installed without desktop
  mode? Open a new PowerShell window and type `anyscribe ui`: the window you
  installed from doesn't see ffmpeg.
- **Mac, and the command says ffmpeg "is already installed, it's just not
  linked"?** Run `brew link ffmpeg`.
- **The terminal finds ffmpeg but the app doesn't?** See
  [Transcribing from the app says ffmpeg (or Deno) is missing](#transcribing-from-the-app-says-ffmpeg-or-deno-is-missing-but-the-terminal-works).

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

### "Your OpenAI account has no credit." (or Groq, OpenRouter, another provider)

The full message reads: "Your OpenAI account has no credit. OpenAI is prepaid:
add credit at https://platform.openai.com/settings/organization/billing and try
again, or use the free option instead (in the dashboard: Settings, then Run
setup wizard, then On this computer)." OpenRouter's reads the same with its
own name and no billing link. Any other provider's reads: "Your Groq account
has no credit. Add credit or check your plan, then try again, or use the free
option instead (...)", with that provider's name.

The provider accepted your key but refused the work because the account has no
money on it. OpenAI's API is prepaid and separate from a ChatGPT subscription:
a new key on an account with no credit fails on the first transcript.
(Technically: OpenAI answers HTTP 429 with `insufficient_quota`, OpenRouter
answers HTTP 402.) anyscribe stops at once instead of retrying, since waiting
never adds credit.

**Fix, either:**

- Add credit, or check your plan, on the provider's billing page (OpenAI: the
  link in the message), then run the same transcription again.
- Or switch to the free option that runs on your computer: in the dashboard,
  **Settings**, then **Run setup wizard**, then **On this computer**. From the
  terminal, `anyscribe onboard --force` and choose **On this computer**.

An ordinary `Rate limited by <provider>` message is different: the account is
fine and busy, and anyscribe waits and retries by itself.

### What the key check says (setup wizard and Settings)

The dashboard asks the provider whether it accepts a key. In the setup wizard
this happens when you press **Next** (or **Test key**) on the key step, before
anything is saved; in **Settings → Providers**, **Test** checks the key you
saved. The answer is one of these:

#### "OpenAI accepted this key." (or another provider's name)

The provider knows the key. It does not prove the account has credit: OpenAI,
for one, is prepaid, so add credit before your first transcript (see
["Your OpenAI account has no credit."](#your-openai-account-has-no-credit-or-groq-openrouter-another-provider)).

#### "OpenAI refused this key. Check that you copied all of it, with no extra spaces."

The provider answered that the key is wrong (HTTP 401 or 403). Usually part of
the key is missing, or a space came along with it. Copy it again from the
provider's site and paste it once more. A revoked or deleted key gives the same
answer: make a new one. If you are sure the key is right, the setup wizard's
**Use this key anyway** keeps it and moves on; the first transcript will tell
you for certain.

#### "OpenAI answered with an error (500). Try again in a minute."

The provider answered, but with an error that isn't about the key (the number
in brackets is its status code; 5xx means a problem on their side). Wait a
minute and test again, or in the setup wizard choose **Use this key
anyway**.

#### "Couldn't reach OpenAI to check the key. Check your internet connection, or continue: the key will be checked on your first transcript."

anyscribe couldn't get any answer from the provider within ten seconds: no
internet, a firewall or VPN in the way, or the provider is down. You can carry
on (in the wizard, press **Next** again): the first transcript checks the key.

#### "Not checked yet: Sarvam has no way to check a key in advance. It will be checked on your first transcript."

Sarvam has no way to check a key without running a paid transcription, so
anyscribe doesn't pretend: it keeps the key (the wizard saves it when you
finish) and shows this in amber instead of a green success. The wizard's key
step shows it from the start, and **Next** goes straight on. If the key is wrong, the first transcript
fails with `Invalid or missing API key for sargam`.

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
to see whether it's the service or the file. The dashboard's **Test** button
(Settings → Providers) does ask the provider; see
[What the key check says](#what-the-key-check-says-setup-wizard-and-settings).

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
transcription on our 6-core test CPU takes about 10 minutes per hour of audio
with Parakeet v3, about 40 with Whisper Large v3 Turbo, and about 2.5 hours with
Whisper Large v3 (`anyscribe model list` shows every model).

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

### "Close setup? The download keeps going in the background while anyscribe stays open." (setup wizard)

You pressed Escape, clicked outside the wizard or clicked **Skip for now**
while it was setting up local transcription. The wizard asks first because
closing it does not stop the download, but does drop your choices:

- **Keep setting up** goes back to the wizard.
- **Close setup** closes it. The download keeps going inside anyscribe as long
  as anyscribe stays open. Your choices on the wizard's screens are saved only
  when you click Finish, so to finish later go to **Settings**, then **Run
  setup wizard**: it opens on the download if it is still running.

Back stays off until the setup finishes.

### "Can't reach anyscribe right now." (setup wizard, during the model download)

The dashboard page lost contact with anyscribe while it was watching the
download: anyscribe was quit, crashed, or the computer slept. The download
runs inside anyscribe, so it carries on only while anyscribe keeps running;
quitting anyscribe stops it.

- **If you closed anyscribe, open it again** (click the app, or type
  `anyscribe ui`). The page keeps asking. When anyscribe answers, the message
  goes away and the page shows the download if it is still running, or "The
  setup stopped before it finished" with a **Try again** button (below).
- **To close the wizard meanwhile:** press Escape or click **Skip for now**,
  then **Close setup** (above).

### "The setup stopped before it finished, because anyscribe was closed." (setup wizard)

anyscribe was closed (or restarted) during the setup, which stops the setup
and its download. Click **Try again** to start it again. Nothing you chose on
the wizard's screens is lost while the wizard stays open.

### `faster-whisper is not installed` / `onnx-asr is not installed`

The local provider is opt-in and needs a one-time install:

```bash
anyscribe local setup --model parakeet-v3
```

That installs the engines (faster-whisper and onnx-asr) into the same Python
environment as anyscribe and downloads the model. The first download needs
internet (~750 MB for Parakeet v3 plus its language check); everything after
that is fully offline. If you set up local transcription before Parakeet
existed, picking a Parakeet model (setup, `anyscribe model pull parakeet-v3`, or
a card in Settings) installs onnx-asr for you.

> `--model` is deliberately required — anyscribe will never pick a model for
> you. `parakeet-v3` is the recommended pick for English and European
> languages, `large-v3-turbo` for Hindi.

### `No module named pip` during local setup

Your anyscribe lives in an environment without pip, which is what
`uv tool install anyscribe` makes. anyscribe then installs with
`uv pip install --python <that environment>` when `uv` is on your PATH. If you
see this error, `uv` isn't on the PATH of the shell that ran anyscribe: open a
new terminal, or install the engines yourself with
`uv tool install "anyscribe[local]" --force`.

### `open() got an unexpected keyword argument 'metadata_errors'`

PyAV 19 (released September 2026) removed an option faster-whisper 1.2.1 <!-- version-pin-ok -->
uses, so every local Whisper run crashed. anyscribe now installs `av<19`;
re-running `anyscribe local setup --model <id>` downgrades a broken install.
If the dashboard (`anyscribe ui`) was running when setup replaced PyAV, it
says **Restart anyscribe to finish setting up local transcription**: the
running server still holds the old PyAV, so stop it (Ctrl+C) and start it
again.

### A model shows as "incomplete"

Its download was interrupted, so some files are missing and anyscribe won't
use it (it never counts as downloaded, and the language check won't switch to
it). Click **Incomplete: download again** in Settings → Local, or run
`anyscribe model pull <id>`; the download starts again.

### "Detected Hindi … no Whisper model to use instead is downloaded"

Your default is Parakeet, the audio is in a language Parakeet doesn't cover,
and there's no Whisper model to hand it to. Nothing was written. Download one:

```bash
anyscribe model pull large-v3-turbo
```

then run the same command again. If the language check guessed wrong (it
checks the language at the start, middle and end of each recording), set the
language yourself:
`anyscribe "<file>" --language en`.

### "Parakeet needs its language check (Whisper Tiny …)"

The 75 MB language-check helper was deleted. `anyscribe model pull tiny`
brings it back, or set an explicit language (`--language en`) to skip the
check.

### Checking what's actually installed

```bash
anyscribe local status
```

Reports the engines (faster-whisper's version, whether onnx-asr is installed),
whether ffmpeg is present, which models are cached, disk usage, and how
anyscribe was installed. It always exits 0, so it's
safe to run before setup.

### Model weights look corrupted

Delete and re-download in one step:

```bash
anyscribe model reinstall parakeet-v3 --yes
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

> **Using local transcription only?** That counts. Once the local engines are
> installed (`anyscribe local setup --model parakeet-v3`, or the **Set up local
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

A tray is already active: it holds a lock file (`~/.anyscribe/tray.lock`) while it
runs, so a second copy steps aside instead of colliding with the first.

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

### I installed over SSH / on a machine with no desktop and the tray isn't there

That's expected. The tray icon needs a graphical session (a desktop you are
logged in to), and an SSH session or a server has none. anyscribe still runs:
`anyscribe desktop install` starts the dashboard without its tray icon and tells
you so:

```
Tray icon: not running (no graphical session or tray support here). The dashboard works without it; the tray will start at your next graphical login.
```

Check it any time:

```bash
anyscribe desktop status
```

It shows `Tray running: no` and `Healthy: yes` with the reason
`Running without its tray icon (no graphical session or tray support).` The
dashboard answers at `http://127.0.0.1:8457`; the tray starts by itself the next
time you log in to a desktop on that machine. The tray's log
(`~/.anyscribe/logs/tray.log`) has one line saying why it could not start.

> **Tip:** the one-line installer already skips desktop mode on a Linux machine
> with no graphical session, so you only see this if you ran
> `anyscribe desktop install` yourself.

### Windows didn't show a security warning when I installed

That's expected. Windows' SmartScreen warning (and macOS's Gatekeeper prompt) is
for apps downloaded through a web browser. Desktop mode doesn't download an app:
it builds the small launcher on your own machine from the anyscribe you just
installed, with nothing to sign. On a Mac this showed no Gatekeeper prompt in our
test; we have not yet confirmed the whole Windows path, so if Windows does warn
you when you click the app, tell us.

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

## Tailnet sharing

These apply only when you've turned on sharing (`anyscribe config set tailnet on`,
`anyscribe ui --tailnet`, or **Settings → Sharing**). In every case the dashboard
still starts on your own computer; anyscribe prints one line starting
`Tailnet sharing is on but not working:` and the Settings card shows the same
reason and fix. Fix the cause, then restart `anyscribe ui` (or flip the switch in
Settings off and on).

### `Tailscale isn't installed on this computer.`

anyscribe looks for the `tailscale` command (on a Mac, also inside the Tailscale
app). Install Tailscale from [tailscale.com/download](https://tailscale.com/download)
and sign in, or turn sharing off:

```bash
anyscribe config set tailnet off
```

### `Tailscale is installed but not running or not signed in.`

Tailscale is there but not connected. Open the Tailscale app and sign in, or run:

```bash
tailscale up
```

### `Tailscale won't let your user change its sharing settings.`

On Linux, Tailscale only lets root or its "operator" change sharing. Make your user
the operator once:

```bash
sudo tailscale set --operator=$USER
```

### `HTTPS sharing (Serve) isn't enabled on your tailnet yet.`

Your tailnet has to allow HTTPS certificates once. The message ends with a
`login.tailscale.com` link: open it, approve, and restart `anyscribe ui`. If there's
no link, turn on **HTTPS Certificates** on the DNS page of the Tailscale admin
console.

### `Port 8457 is already shared on your tailnet by something else; anyscribe left it alone.`

Another program already uses that port number with `tailscale serve`, so anyscribe
won't replace its rule. Start the dashboard on a different port:

```bash
anyscribe ui --port 9000
```

(`tailscale serve status` shows what holds each port.)

### The link says "bad gateway" or doesn't load

The dashboard isn't running, but its Tailscale rule is still there. A normal stop
(Ctrl+C, the **Shutdown** button, quitting the tray) removes the rule. It stays
behind if anyscribe was killed hard (power loss, `kill -9`), and it can stay behind
if Tailscale itself is stuck when you quit the tray, because the tray force-stops
the dashboard after about 8 seconds. To clear it, start the dashboard shared for
one run and stop it normally (Ctrl+C or the **Shutdown** button), using your port
number:

```bash
anyscribe ui --tailnet --port 8457
```

anyscribe reuses the rule, and the clean stop removes both the rule and its note in
`~/.anyscribe/tailnet-owned.json`. Removing the rule by hand instead
(`tailscale serve --https=8457 off`) leaves that note behind, and one case then goes
wrong: if you later make exactly the same rule by hand, anyscribe can't tell it apart
from its own and removes it on its next clean stop.

With sharing off, anyscribe never touches Tailscale, so it won't clean this up for you.

### `Tailscale no longer has the share (removed outside anyscribe, or cleared when Tailscale signed out).`

The Settings card shows this when the dashboard was shared but its Tailscale rule
has gone (someone ran `tailscale serve reset` or `--https=<port> off`, or signing
out of Tailscale cleared it). The page
re-checks each time you open it or come back to the window. Flip the switch off
and on to share it again.

### `Tailscale says it is stopped or signed out on this computer, so other devices can't reach the link right now.`

The Settings card shows this when the dashboard was shared but Tailscale has since
stopped or signed out. The link can't open meanwhile, so the card stops showing it.
Open Tailscale and sign in (or run `tailscale up`); the link comes back by itself,
and the card shows it again the next time you open the page or come back to the
window.

anyscribe keeps holding the share meanwhile, so it still answers its exact tailnet
name during the outage (no request from your tailnet can arrive while Tailscale is
stopped anyway).

### `anyscribe couldn't get an answer from Tailscale, so it can't confirm the link works.`

The Settings card shows this, under "On, but the link isn't confirmed right now.",
when one check of Tailscale failed or was slow, or Tailscale was still starting.
The link may not open, so the card hides it until the next check. Other devices may
still be able to open the page meanwhile: anyscribe keeps holding the share, and the
card never claims the page is only on this computer. It checks again when you come
back to the page.

Opened on another device through the link, the card says instead: "On. You're
reading this over the tailnet link, so it works." That is true: Tailscale delivered
the page.

### `A share you set up yourself; anyscribe will leave it in place.`

Not an error. You had already made the same `tailscale serve` rule by hand, so
anyscribe uses it for the link and does not remove it when it stops. Remove it
yourself with `tailscale serve --https=<port> off` when you no longer want it.

### `anyscribe left your own Tailscale rule on port 8457 in place, but no longer answers through it.`

You switched sharing off while the dashboard was using a rule you made by hand.
anyscribe never removes your rule, but it stops answering on the tailnet link, so
your other devices get a refusal instead of the dashboard. With sharing off anyscribe
no longer checks Tailscale, so this note stays until you flip the switch or restart,
even if you have removed the rule since. To remove it, run
`tailscale serve --https=8457 off` (your port number), or switch sharing back on.

### `Other devices are refused now. anyscribe couldn't remove its Tailscale rule (...)`

You switched sharing off (or stopped the dashboard), and anyscribe stopped
answering on the tailnet link at once, but removing its own `tailscale serve` rule
failed (the reason is in the brackets: Tailscale didn't answer, refused, or the
record file couldn't be written). Nothing on your tailnet can use the page. anyscribe
tries again when the dashboard stops; or remove the rule yourself with the command
the note shows, `tailscale serve --https=8457 off` (your port number). If you remove
it by hand, see [the link says "bad gateway"](#the-link-says-bad-gateway-or-doesnt-load)
for clearing anyscribe's record of it.

### "anyscribe only answers on this computer's own address..."

You opened the dashboard under a name it doesn't answer. It answers only at
`127.0.0.1` and `localhost` on this computer, and at its own tailnet link while
anyscribe holds its share (from a successful share until you switch it off, the
share is removed outside anyscribe, or the dashboard stops; also while Tailscale is
briefly down). This blocks web pages from reaching it under their own name. Open it
at `http://127.0.0.1:8457` on this computer.

If you see this on another device through a Tailscale link, one of two things
happened:

- Sharing is off for this dashboard, and the link is a rule left behind or one you
  made by hand with `tailscale serve`. A rule you made by hand: turn sharing on (the
  Settings switch applies it now; `anyscribe config set tailnet on` at the next
  start), and anyscribe uses it and leaves it in place. A leftover from a hard stop:
  run `anyscribe ui --tailnet` and stop it normally to clear it (see
  [the link says "bad gateway"](#the-link-says-bad-gateway-or-doesnt-load)).
- Sharing is on, but Tailscale no longer has the share (removed outside anyscribe,
  for example `tailscale serve reset`, or cleared when Tailscale signed out), so
  anyscribe let go of it. Flip the switch off and on at
  the computer running anyscribe (open it there at `http://127.0.0.1:8457`).

If you reach the dashboard through another proxy, tunnel or hostname, it refuses that
name (a proxy that passes requests on as 127.0.0.1 or localhost still gets through,
and the Settings card then warns you); open it at 127.0.0.1, or share it with the
tailnet setting.

### `Couldn't read your anyscribe config, so tailnet sharing is off for this run.`

`~/.anyscribe/config.yaml` has a mistake in it, so anyscribe can't tell whether
sharing is on. The dashboard starts on your own computer. Fix the file (or see
`anyscribe config path`), then restart `anyscribe ui`.

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
