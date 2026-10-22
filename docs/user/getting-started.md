---
summary: One installer command, one setup wizard, one transcript — then the two ways to run anyscribe (desktop app or CLI) and where to go next.
title: Getting Started
read_when:
  - First time setting up anyscribe
  - You want the fastest path to a working transcription
  - You want anyscribe always running (desktop app, menu bar, start at login)
  - You want to remove the desktop app
  - You're an agent / script and want the headless setup form
---

# Getting Started

Install anyscribe, run setup, get your first transcript — about 5 minutes.

By the end of this guide you will have:
- anyscribe installed on your machine
- An Obsidian vault ready to browse your transcripts
- Your first video transcribed to markdown
- An **anyscribe** app icon that opens the dashboard, if you used the one-line installer

> **anyscribe has three equivalent surfaces.** The Web UI, the terminal wizard, and the headless flag-driven CLI all cover the full product. Every *setting* can be changed from either the CLI or the Web UI. A few commands are CLI-only: `batch`, `download`, `logs`, `doctor`, `update`, `migrate`, `install-skill`, `desktop`, and `tray`. Pick whichever fits:
>
> - **Prefer clicking?** → `anyscribe ui` opens a browser dashboard with a setup wizard on first launch. See Option A in Step 2.
> - **Prefer typing?** → `anyscribe onboard` runs an arrow-key terminal wizard. See Option B.
> - **Writing a script or an AI agent?** → `anyscribe onboard --provider X --api-key $KEY --yes --json`. See Option C.
>
> All three write the same config and land you in the same place. Transcriptions you start from one surface show up in all of them.

> **Everything runs locally.** The Web UI at `http://127.0.0.1:8457` is a server on your own machine — no cloud account, no sign-up. anyscribe has no analytics or telemetry. It goes online to download a source you point it at, to call the transcription provider you set up, and to install dependencies and Whisper models when you set them up. It also checks for new versions when you run `anyscribe update --check` or `anyscribe doctor` (through pip's package index, or your git remote for a cloned install), and upgrades yt-dlp when your copy is over 60 days old. Local files with the local provider work with no internet connection, and your audio never leaves your machine.

## What you need

- **A computer running macOS, Linux, or Windows** (native Windows and WSL2 both work). The one-line installer below brings the rest: Python, ffmpeg, yt-dlp, and Deno for YouTube.
- **Then pick one engine:**
  - **Free, offline** — the **local** provider. No API key, no internet, runs Whisper on your machine. Downloads a model once during setup.
  - **Or an API key** from one provider — OpenAI is the default. Get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys); transcription costs about $0.0045/minute — a 10-minute video costs around 5 cents. Six cloud providers are supported alongside local — see [providers.md](providers.md) for the comparison.

> **Later, if you want cheaper or more accurate:** each provider offers a few models you can switch between — see [providers.md](providers.md). You don't need to think about this to get started; the defaults are good.

> **New to the command line?** You'll be typing commands in your Terminal app (macOS), terminal emulator (Linux), or Command Prompt / PowerShell (Windows). Every command in this guide starts with `anyscribe` — just copy-paste and press Enter.

## Step 1 — Install

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.ps1 | iex
```

The installer checks for Python 3.11+, ffmpeg, yt-dlp, and a JavaScript runtime for YouTube (Deno, or Node 22+ if you already have it), installs whatever's missing, then installs anyscribe with the tray included. On Windows it also fixes your PATH so `anyscribe` works from any terminal (on Windows, ffmpeg needs winget or Chocolatey — the installer tells you if neither is present).

**Then it sets up desktop mode:** an **anyscribe** app icon, anyscribe started now and at every login, and the dashboard opened in your browser. See [Two ways to install](#two-ways-to-install) for what that means and how to undo it. Want the command-line tool only? Add `--no-desktop`:

```bash
curl -fsSL https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.sh | bash -s -- --no-desktop
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.ps1))) -NoDesktop
```

> **Why the longer Windows line?** The plain `irm … | iex` form can't pass options to the script, so skipping desktop mode needs this wrapped form. If the desktop step fails for any reason, the installer warns you, finishes the normal install, and tells you to retry later with `anyscribe desktop install`.

Verify it worked:

```bash
anyscribe --version
```

You should see `anyscribe` followed by a version number.

> **`scribe` and `ascli` are shorter aliases.** Every `anyscribe` command in this guide also works typed as `scribe` or `ascli` — same tool, fewer letters. Use whichever you like.

**Already have Python 3.11 or newer and just want the package?**

```bash
pip install "anyscribe[tray]"
```

The `[tray]` extra is what gives you the tray icon and the desktop app (see [Two ways to install](#two-ways-to-install)); pip doesn't set up the desktop app by itself, so run `anyscribe desktop install` afterwards if you want it. Plain `pip install anyscribe` works too, and you can add the extra later. Installing anyscribe with pip also installs yt-dlp and its default extras. Install ffmpeg yourself and, for YouTube, Deno 2.3+ (`brew install deno`, or [deno.com](https://docs.deno.com/runtime/getting_started/installation/)) unless Node 22+ is available. Run `anyscribe doctor` to see what is missing. On an older Python, pip quietly installs an older anyscribe instead; check with `python3 --version` first.

> **Want to install Python and the dependencies by hand?** See the [Appendix: manual install](#appendix-manual-install) at the bottom.

> **`command not found: anyscribe` on Windows?** Use `python -m anyscribe` as a drop-in replacement — it always works. See [Troubleshooting](#troubleshooting).

## Step 2 — First run

You can set up anyscribe either way — both paths save the same config, so pick whichever feels natural.

### Option A (recommended): Web UI

```bash
anyscribe ui
```

Opens a local dashboard at `http://127.0.0.1:8457`. A **setup wizard pops up on first launch**:

1. **Pick a provider** — cards for `openai` (general purpose, multilingual), `deepgram` (fast, native diarization), `groq` (cheapest and fastest cloud Whisper), `elevenlabs` (high accuracy, 90+ languages), `sargam` (Sarvam AI, Indic languages), `openrouter` (many models, one API), plus `local` for free offline transcription on your own machine.
2. **Paste your API key.** The **Test key** button performs a provider check where available; for Groq, Sarvam, and OpenRouter it only confirms that a key was entered. Success does not guarantee that transcription will succeed. This step is skipped for `local`.
3. **Choose whether to also enable offline transcription** — installs faster-whisper and a Whisper model so you can also transcribe offline, for free, whenever you choose it (`-p local`).
4. **Confirm your workspace** — where your transcripts live, default `~/anyscribe/`.

Click around — no commands to memorize.

Close the tab when you're finished; to stop the server, hit Ctrl+C in the terminal or click **Shutdown** in the sidebar.

### Option B: Terminal (interactive)

```bash
anyscribe onboard                   # macOS / Linux
python -m anyscribe onboard      # Windows (first time — prints PATH fix)
```

The wizard uses arrow-key selectors — navigate with **↑↓** and press **Enter** to select:

1. **Check your system** — makes sure `yt-dlp` and `ffmpeg` are installed. Offers to install missing ones.
2. **Choose your provider** — 7 options: OpenAI (default), OpenRouter, ElevenLabs, Sarvam AI, Deepgram, Groq, Local.
3. **Choose that provider's model** — only if it offers more than one. The first is the recommended default; press Enter to take it.
4. **Enter your API key** — stored locally at `~/.anyscribe/.env`. Never sent anywhere except your provider.
5. **Also enable offline transcription?** (optional) — installs faster-whisper and a Whisper model so you can also transcribe offline, for free, whenever you choose it (`-p local`).
6. **Add more provider keys** (optional) — configure multiple providers now or later.
7. **Configure Instagram** (optional) — choose which browser to read Instagram cookies from. Needed only for rate-limited or private reels.
8. **Choose language** — auto-detect (default) or pick a specific language.
9. **Keep audio files** — whether to save the transcription audio to `~/.anyscribe/downloads/audio/`.
10. **Local file handling** — what to do with original files when transcribing local audio/video (skip/copy/move/ask).
11. **Post-transcription downloads** — whether anyscribe should offer to download the full video after each transcription (never/ask/always).
12. **Choose workspace location** — where to store transcripts (default: `~/anyscribe/`).
13. **Create workspace** — sets up your Obsidian vault at the chosen location.

> **Re-run anytime:** `anyscribe onboard --force` to change settings — it shows your current config and lets you choose which parts to update. `anyscribe onboard --skip-deps` to skip the dependency check. Or use the Web UI: Settings → **Run setup wizard**.

### Option C: Headless (for agents + scripts)

If you're automating anyscribe (CI, a Claude Code agent, a provisioning script), bypass the wizards entirely with `anyscribe onboard --yes`:

```bash
anyscribe onboard \
  --provider openai \
  --api-key "$OPENAI_API_KEY" \
  --yes --json
```

Every interactive field maps to a flag. Full reference: [commands.md → anyscribe onboard](commands.md#anyscribe-onboard).

## Step 3 — First transcript

Pick any YouTube video and run:

```bash
anyscribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

Replace `VIDEO_ID` with a real video ID. A short video (under 5 minutes) is good for your first try.

> **No subcommand needed.** Just `anyscribe "url"` — it knows you want to transcribe. You can also write `anyscribe transcribe "url"` explicitly, but it's not required.

> **Always wrap URLs in quotes** (`"..."`). Shells like zsh break URLs with `?` in them. Or run `anyscribe transcribe` with no URL and paste it when prompted — no quoting needed.

You'll see:

```
Transcription saved: ~/anyscribe/sources/youtube/how-to-make-perfect-coffee.md
  Title:    How to Make Perfect Coffee
  Duration: 4:32
  Language: en
  Words:    847
```

### Also try

```bash
# Local audio/video file (mp3, mp4, m4a, wav, opus, ogg, flac, webm, aac, wma)
anyscribe /path/to/podcast.mp3

# Instagram reel
anyscribe "https://www.instagram.com/reel/SHORTCODE/"

# Just download, no transcription
anyscribe download "https://www.youtube.com/watch?v=VIDEO_ID"

# From clipboard (copy a URL first)
anyscribe transcribe --clipboard
```

### Browse it in Obsidian

Open Obsidian and select "Open folder as vault", then choose:

```
~/anyscribe/
```

> **Tip:** This folder is in your home directory — it shows up in Finder and file pickers by default. If you chose a custom workspace path during setup, use that path instead.

You'll see:
- **`_index.md`** — a table of all your transcripts, newest first
- **`sources/youtube/`**, **`sources/instagram/`**, and **`sources/local/`** — transcripts organized by source
- **`daily/`** — a log of what you transcribed each day

Each transcript has YAML properties that Obsidian can search and filter:

```yaml
title: "How to Make Perfect Coffee"
platform: youtube
duration: "4:32"
language: en
word_count: 847
reading_time: "4 min"
tags: [transcript, youtube]
```

## Two ways to install

anyscribe runs the same way underneath either way; what differs is whether you ever see a terminal.

| | **Desktop mode** | **CLI mode** |
|---|---|---|
| How you get it | The one-line installer (default), or `anyscribe desktop install` | `pip install anyscribe`, or the installer with `--no-desktop` |
| How you open the dashboard | Click the **anyscribe** app icon | Run `anyscribe ui` in a terminal |
| Runs in the background | Yes, in your menu bar (macOS) or system tray (Windows, Linux), started at every login | Only while the terminal window running `anyscribe ui` is open |
| Claude Code, MCP, terminal commands | Work | Work |

> **Claude Code does not need the app open.** The skill and the MCP server run each transcription themselves and exit; they never talk to the dashboard. Transcripts Claude makes show up in the dashboard's History the next time you open it, because it reads them straight from your vault.

### Desktop mode

This is what the one-line installer set up, using one command you can also run yourself:

```bash
anyscribe desktop install
```

It does three things:

1. **Adds an anyscribe app.** On macOS it's in your Applications folder (`~/Applications/anyscribe.app`); on Windows, in the Start menu; on Linux, in your app menu.
2. **Starts anyscribe at login.** A small icon sits in your menu bar (macOS) or system tray (Windows, Linux) with the dashboard's server running behind it. This is called a *login item*: a file your computer reads when you log in to decide what to start.
3. **Starts it now and opens the dashboard** at `http://127.0.0.1:8457`.

**To open the dashboard:** click the app, the way you open any other.

- **macOS:** press ⌘ Space, type `anyscribe`, press Enter (or open it from Applications)
- **Windows:** Start menu → type `anyscribe` → click it
- **Linux:** your app menu → **anyscribe**

Closing the browser tab leaves anyscribe running, so the next click opens instantly. If it wasn't running (you quit it earlier), clicking the app starts it first.

**To stop it:** click the tray icon → **Quit**. It starts again at your next login, or the next time you click the app.

**To turn off start-at-login but keep the app:** open the dashboard → **Settings** → **Startup** → switch off **Start at login**. (The CLI equivalents are `anyscribe uninstall-service` and `anyscribe install-service`.) This doesn't stop a copy that is already running; Quit it from the tray icon.

> If the tray extra isn't installed, the **Start at login** toggle refuses with a message telling you to run `pip install "anyscribe[tray]"` first — better than a login item that silently fails.

**To check it:**

```bash
anyscribe desktop status
```

It says whether the app is installed, whether it's running, and, if something is wrong (say you reinstalled Python), what's wrong and the command that fixes it.

**To remove it:**

```bash
anyscribe desktop uninstall
```

This stops anyscribe (any transcription in progress is cancelled and resumes from where it stopped the next time you run it), then removes the app, the login item and the icons. Your transcripts in `~/anyscribe/`, your settings and your API keys are left exactly as they were, and the `anyscribe` command keeps working.

> **Upgraded anyscribe with pip?** Run `anyscribe desktop install` once afterwards so the app and login item point at the new copy.

### CLI mode

```bash
anyscribe ui
```

`anyscribe ui` runs the dashboard from a terminal window, so it stops when you close that window (or press Ctrl+C, or click **Shutdown** in the sidebar). Nothing is added to your Applications folder or your login items. Everything else (transcribing from the terminal, Claude Code, MCP) works exactly the same.

**The way back in.** Closed the tab, clicked Shutdown, or rebooted? Run `anyscribe ui` again, or click the anyscribe app if you're in desktop mode. Your library, config, and API keys are untouched; nothing about stopping the server touches your data.

See [Commands → anyscribe desktop](commands.md#anyscribe-desktop), [anyscribe tray](commands.md#anyscribe-tray) and [anyscribe install-service](commands.md#anyscribe-install-service) for the full reference.

## Where next

Three doors, depending on how you want to use anyscribe:

- **[Use anyscribe from your AI tools](agents.md)** — the Claude Code skill and the MCP server, so you can say "transcribe this" instead of typing commands
- **[Commands](commands.md)** — every command, flag, and example
- **[Providers](providers.md)** — cost, accuracy, languages, and how to switch
- **[Troubleshooting](troubleshooting.md)** — every common error and its fix, when something goes sideways

Handy things you can do right now:

- **Speaker diarization** — `anyscribe "url" --diarize` identifies who said what (auto-detects number of speakers). Set up Deepgram first: `anyscribe config set deepgram_api_key YOUR_KEY` ($200 free credit at [console.deepgram.com](https://console.deepgram.com/))
- **Batch process** — `anyscribe batch urls.txt` to transcribe a list of URLs
- **See what will run** — `anyscribe config` shows the provider + model of your next transcription and every alternative
- **Switch providers** — `anyscribe config set provider elevenlabs` (or let a tier choose: `anyscribe config set quality accuracy`)
- **Try JSON output** — `anyscribe "url" --json` for scripting
- **Check health** — `anyscribe doctor` verifies everything is working
- **Update** — `anyscribe update` pulls the latest version
- **View all commands** — `anyscribe --help`

## Instagram (optional)

Public reels usually work out of the box. If you hit rate-limiting, or want
to transcribe reels from accounts you follow, anyscribe can read your existing
browser session — no password needed:

```bash
anyscribe config set instagram.browser firefox
```

Supported browsers: `firefox`, `chrome`, `safari`, `brave`, `edge`, `chromium`,
`vivaldi`, `opera`.

> **Tip:** Firefox tends to work most reliably on macOS. Chrome's cookie
> encryption can make extraction flakier.

> **Note for upgraders:** If you onboarded with anyscribe < 0.8.3, you may have <!-- version-pin-ok -->
> an `INSTAGRAM_PASSWORD` in your `~/.anyscribe/.env`. It's no longer used
> and can be removed.

## Troubleshooting

Everything that commonly goes wrong — `command not found: anyscribe`, missing API keys, shells mangling URLs, yt-dlp failures, Instagram `login_required`, wrong language, slow long videos — is covered with fixes in **[troubleshooting.md](troubleshooting.md)**.

The one worth knowing up front: if `anyscribe` isn't recognized, `python -m anyscribe` is a drop-in replacement that always works (`python -m anyscribe onboard`, `python -m anyscribe transcribe "..."`).

## Appendix: manual install

Prefer to install each piece yourself? The one-line installer in Step 1 does all of this for you — this path is for people who'd rather see every step.

**1. Python 3.11 or newer.** Check what you have:

```bash
python3 --version      # macOS / Linux
python --version       # Windows
```

You should see something like `Python 3.12.x`. If you get an error or a version below 3.11:

**macOS:**
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install python3 python3-pip python3-venv
```

Then run `python3 --version` again. If it still shows 3.10 or older (Ubuntu 22.04 does), install a newer Python alongside it: `sudo apt install python3.11 python3.11-venv`. It does not change which Python `pip` uses, so step 3 below uses pipx on Linux. Debian 11 has no Python 3.11 package; upgrade to Debian 12 first. The simplest route on any Linux is still the one-line installer at the top of this guide, which does all of this for you.

**Windows:**
Download from [python.org/downloads](https://www.python.org/downloads/) and run the installer. **Check "Add Python to PATH"** during installation.

> **Don't have Homebrew?** It's the standard package manager for macOS. Install it from [brew.sh](https://brew.sh).

**2. ffmpeg and Deno.** ffmpeg converts audio; Deno runs the small JavaScript puzzle YouTube sets before it hands over media (Node 22+ works too, if you already have it; skip Deno then). yt-dlp, which fetches the video, comes with anyscribe in step 3.

**macOS:**
```bash
brew install ffmpeg deno
```

No separate yt-dlp step: anyscribe installs it in step 3.

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ffmpeg pipx unzip
curl -fsSL https://deno.land/install.sh | sh
```

No separate yt-dlp step on Linux: anyscribe installs yt-dlp inside its own environment in step 3. Deno's script puts the program in `~/.deno/bin` and adds it to your shell profile; anyscribe finds it there even before you open a new terminal.

**Windows:**
```powershell
winget install ffmpeg
winget install DenoLand.Deno
```

No separate yt-dlp step: anyscribe installs it in step 3.

**3. anyscribe itself.** Install with the same Python you checked in step 1, so a second, older Python's `pip` cannot sneak in.

**macOS:**
```bash
python3 -m pip install "anyscribe[tray]"
```

If Homebrew's Python answers "externally-managed-environment", use pipx instead: `brew install pipx`, then `pipx install "anyscribe[tray]"` and `pipx ensurepath`.

**Windows:**
```powershell
python -m pip install "anyscribe[tray]"
```

**Linux (Debian 12, Ubuntu 24.04 and newer, where `python3` is already 3.11+):**
```bash
pipx install "anyscribe[tray]"
pipx ensurepath
```

**Linux (Ubuntu 22.04, using the python3.11 from step 1):**
```bash
pipx install --python /usr/bin/python3.11 "anyscribe[tray]"
pipx ensurepath
```

Then open a new terminal. Plain `pip install` is refused by the system Python on Debian 12 and Ubuntu 24.04 ("externally managed"), and on Ubuntu 22.04 it belongs to the old Python and quietly installs an older anyscribe.

Verify:

**macOS / Linux:**
```bash
anyscribe --version
```

**Windows:**
```bash
python -m anyscribe --version
```

You should see `anyscribe` followed by a version number.

> **Why `python -m` on Windows?** pip installs `anyscribe.exe` to a Scripts directory that's usually not on PATH. `python -m anyscribe` always works because it uses the same Python you installed with. On first run, it will print the exact PowerShell command to add `anyscribe` to your PATH permanently — after that, you can use `anyscribe` directly.

**4. Check everything landed:**

```bash
anyscribe doctor
```

Then head back to **Step 2 — First run** above.

> **Developing on anyscribe?** [Clone the repo](https://github.com/rishmadaan/anyscribe) and install it editable — see the building docs.

## License and source

anyscribe is free software under [GNU AGPLv3 or later](https://github.com/rishmadaan/anyscribe#license),
with no warranty. Commercial use is allowed under the license terms. If you
distribute a modified version or let others use one over a network, follow its
source-sharing requirements. Your transcripts are not automatically covered by
the application's license. The dashboard sidebar links to source and dependency
notices; CLI help links to license and source information.
