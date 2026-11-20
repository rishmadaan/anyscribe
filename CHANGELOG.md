# Changelog

What changed in each release of anyscribe, newest first.

This file is for **users** — what changed for you, and whether you need to do
anything about it. `BACKLOG.md` is the developer-facing companion: the same
releases with implementation detail, plus the roadmap and parked ideas.

Install or upgrade with `pip install --upgrade anyscribe`. Versions follow
SemVer; while we're on `0.x`, a minor bump can carry a breaking change.

---

## Unreleased

Getting in: fixes for the places a first-time user got stuck during install
and setup, from the 2026-11-20 onboarding audit. The installer and website
changes reach you as soon as they are merged (the install line always fetches
the latest installer); the dashboard and transcription changes arrive with
the next release.

**Installing**
- **Mac without Homebrew:** the one-line installer now lets Homebrew ask for
  your password. Before, under `curl … | bash` Homebrew refused to ask and the
  installer stopped without a word. If Homebrew still doesn't finish, the
  installer says so and what to do: "Homebrew didn't finish installing, so
  anyscribe can't continue. …"
- **Windows on the website:** the first screen shows the full Windows install
  line with its own copy button, next to the Mac one, and each says how to open
  Terminal or PowerShell and paste. The getting-started guide no longer
  suggests Command Prompt, which can't run the Windows line.
- **ffmpeg missing at the end of an install:** both installers now check that
  ffmpeg really is there. If it isn't, the last box says "anyscribe is
  installed, but can't transcribe yet" with the command to install it, instead
  of "anyscribe is ready!".
- **The last box says how to open anyscribe:** when desktop mode was set up,
  click the app (on a Mac: press Cmd and Space, type anyscribe, press Return);
  otherwise, when the terminal you installed from can't find the
  `anyscribe` command yet, open a new terminal window first (the full path for
  that window is printed under the box).
- **Windows: the window stays open when the installer fails,** so you can read
  the error and the manual steps. Before, it closed the whole PowerShell
  window.

**Setting up**
- **ffmpeg in the setup wizard:** "On this computer" now says "One more thing:
  ffmpeg" with the install command and a **Check again** button when ffmpeg is
  missing, instead of looping silently after the download.
- **Real key checks:** Groq and OpenRouter keys are now checked with the
  provider (before, any text passed). Every check answers in plain words:
  accepted, refused (check you copied all of it), an error from the provider,
  or couldn't reach it. Sarvam, which can't check a key in advance, says
  "Not checked yet" in amber on its key step, and Next goes straight on. Pressing **Next** on the key step runs the
  check; a refused key stays on the step, with **Use this key anyway**.
- **OpenAI is prepaid:** the OpenAI key step (dashboard and `anyscribe
  onboard`) says to add credit first.
- **Closing the wizard during the model download asks first:** Escape, a click
  outside and **Skip for now** show "Close setup? The download keeps going in
  the background while anyscribe stays open. …" with **Keep setting up** and
  **Close setup**; the wizard is never locked; Back and the model choices are
  off until the setup finishes. Reloading the page picks the running download back up
  instead of showing an error. If the page can't reach anyscribe, the wizard
  says "Can't reach anyscribe right now"; if anyscribe then reports no setup
  and no result (after a restart, for example), it says "Setup didn't
  finish", with **Try again**. A setup that fails says "anyscribe couldn't
  finish setting up local transcription. Click Try again."; the technical
  details stay in the install log, which opens only when you click it.

**Transcribing and reading**
- **"Your OpenAI account has no credit."** An account with no credit now gets
  that message, with the billing link and the free option, and anyscribe stops
  at once. Before, it said "Rate limited, wait and retry" and retried. The same
  goes for OpenRouter's out-of-credit answer.
- **Read transcript:** the Done screen's main button opens the transcript, and
  the transcript page shows it formatted (headings, quotes, bold, links)
  instead of raw markdown. The "already transcribed" link now also works with
  Windows file paths.

---

## 0.19.0 — 2026-11-20

**Added**
- **Transcribe on your own computer without an API key, faster and more
  accurately: Parakeet v3.** A new local model (`parakeet-v3`, NVIDIA's
  Parakeet, ~670 MB) is as accurate as the best Whisper model on English in
  our test, at about four times its speed: roughly 10 minutes per hour of
  audio on our 6-core test desktop. It covers English and 24 European
  languages. `anyscribe local setup --model parakeet-v3`.
- **A language check in front of Parakeet.** Before Parakeet runs, a 75 MB
  helper checks the language at the start, middle and end of each recording
  (speech only, so leading silence doesn't fool it). If any of them is a
  language Parakeet doesn't know (Hindi, for example), anyscribe uses Whisper
  Large v3 Turbo instead and says so in the terminal, in `--json` `notes`, in
  the dashboard, and in the transcript. If the check can't tell, it uses
  Whisper when one is downloaded, or runs Parakeet and says the check was
  unsure. If no Whisper model is downloaded, it stops and tells you what to
  download.
- **First run asks one question instead of "which API?".** The setup wizard
  (dashboard and `anyscribe onboard`) starts with *On this computer — free,
  private, no API key* vs *With a cloud service*. On this computer asks what
  language your audio is in and suggests a model, with the reason in plain
  words. **Help me choose** in Settings asks the same question any time.
- **Model cards.** Settings → Local, the setup window and `anyscribe model
  list` show each model's accuracy and speed out of 5 (measured, not
  guessed), how long an hour of audio takes, download size and memory, with
  older or slower models under **More models** and the reason they're there.
- Transcripts made locally now record the model that ran (`model:` in the
  frontmatter and in `--json`).

**Changed**
- **The local default model changes only to a model that is ready.**
  `anyscribe config set local_model <id>` (and the dashboard and agents) now
  refuse a model that isn't downloaded yet, instead of saving it and failing
  on the next run, and name the command to download it. In the dashboard,
  picking a model that isn't downloaded downloads it (with Parakeet's
  language check) and switches only once it is ready; if the download fails,
  your default stays as it was.
- **Help me choose in Settings only suggests.** It highlights the suggested
  model and offers one button ("Use Parakeet v3 + Whisper Large v3 Turbo
  (downloads …)"); nothing downloads or changes until you click it.
- With no API key set, the "key not set" errors and the quality-tier warning
  also mention the free option: `anyscribe local setup --model parakeet-v3`.

**Fixed**
- **Local transcription crashed on new installs** (`open() got an unexpected
  keyword argument 'metadata_errors'`): a new PyAV release broke
  faster-whisper. anyscribe now installs a compatible version; re-run
  `anyscribe local setup --model <id>` to repair an existing install.
- **`anyscribe local setup` failed when anyscribe was installed with
  `uv tool install`** ("No module named pip"). It now installs with `uv`.
- **Whisper sometimes wrote English transcripts all lowercase with no
  punctuation** when a recording started mid-sentence. Fixed for English.
- **Batches with a local model reloaded it for every file** (6-17 s each).
- The dashboard's setup windows scroll when they're taller than the screen,
  and the dashboard fits a phone screen.

**Nothing changes for an existing setup** unless you pick a new model; if you
use a Whisper model for English, `anyscribe local status` suggests trying
Parakeet v3.

---

## 0.18.3 — 2026-11-14

**Fixed**
- **ElevenLabs transcripts had three spaces between every word, and timestamped
  lines were half as long as they should be.** Lines now hold about 30 words
  with single spaces, as documented. Transcripts you already made keep their
  extra spaces; they are invisible in Obsidian's reading view, and
  `anyscribe "<url>" --force` transcribes a video again (a paid engine bills that run again).
- **The dashboard's company logo and footer artwork were missing** (a broken
  image in the sidebar, no drawings along the bottom) in every release since
  0.16.0. Both are back.

**Changed**
- The website opens with a short demo video of the dashboard, and the README
  screenshot shows the current name.

---

## 0.18.2 — 2026-11-09

**Added**
- **Share the dashboard with your other devices over Tailscale** (optional,
  off by default). Turn it on once with `anyscribe config set tailnet on`, or
  with the switch under **Settings → Sharing**. From then on `anyscribe ui`
  also prints a private `https://<machine>.<tailnet>.ts.net:<port>/` link that
  your other computers on your tailnet can open. `anyscribe ui --tailnet` and
  `anyscribe ui --local-only` override it for one run. anyscribe still listens
  only on your own computer and asks Tailscale to pass the page along; it never
  uses Funnel (the public internet) and never replaces or removes a Tailscale
  share it didn't create. The dashboard has no login: anyone on your tailnet
  can use it while it is shared, and anyscribe says so wherever you turn it on.
  If Tailscale isn't installed, signed in or allowed, the dashboard still opens
  on your computer and one line says why and what to do. The dashboard is laid
  out for a computer screen, not a phone. See **Commands → ui** and
  **Troubleshooting → Tailnet sharing**.

**Changed**
- **The dashboard now only answers at its own address.** Whether sharing is on
  or off, it answers at `127.0.0.1` or `localhost` on your computer, and at its
  own Tailscale link while it is shared. This stops a malicious web page from
  reaching your dashboard under another name. If you reached the dashboard
  through another proxy, tunnel or hostname, it now refuses that name (a proxy
  that passes requests on as `127.0.0.1` or `localhost` still works). A
  Tailscale share you set up yourself with `tailscale serve` now needs the
  sharing setting on; anyscribe then uses it and leaves it in place.

---

## 0.18.1 — 2026-11-09

**Fixed**
- **Downloading a local model from the dashboard failed** with
  `'_ProgressTqdm' object has no attribute 'unit'`. New installs pick up a
  newer version of the Hugging Face download library, which switches its
  progress bars off when there's no terminal window, and anyscribe's progress
  tracking didn't expect that. Downloads now finish, and the progress bar
  shows the model's real size instead of roughly double it. If a download
  failed for you, update and press Install again.

**Changed**
- **The recommended local model is now `large-v3-turbo`** (was `base`). It is
  close to the most accurate model and about six times faster than real time
  on a CPU; it's a ~1.6 GB download and needs about 3 GB of free memory. On an
  older laptop, `base` is still the right pick. Nothing changes for an
  existing setup: your chosen model stays your default.

**Added**
- Every local model now says what it's for ("Use it for most people:
  near-best accuracy at good speed. Start here") in the dashboard's model
  picker, first-run setup and `anyscribe onboard`.

---

## 0.18.0 — 2026-10-22

**Added**
- **Desktop mode.** `anyscribe desktop install` adds an **anyscribe** app
  (`~/Applications`, the Applications folder inside your home folder, on macOS;
  the Start menu on Windows; the app menu on Linux),
  starts anyscribe in your menu bar or system tray at every login, starts it
  now, and opens the dashboard. Click the app to open the dashboard; closing
  the browser tab leaves it running; Quit in the tray menu stops it. The
  launcher is generated locally and needs no
  separately signed app download. It avoided Gatekeeper prompts in our Mac
  test; Windows click-through remains unverified.
- `anyscribe desktop status` says whether the app is installed, running and
  healthy, and names the fix when it isn't. `anyscribe desktop uninstall`
  stops anyscribe and removes the app, the login item and the icons; your
  transcripts, settings and API keys stay. `anyscribe desktop open` is what
  the app icon runs. `install`, `uninstall` and `status` take `--json` for agents.
- The one-line installers finish by setting up desktop mode. Skip it with
  `--no-desktop` (macOS / Linux: `... | bash -s -- --no-desktop`) or
  `-NoDesktop` (Windows:
  `& ([scriptblock]::Create((irm <installer url>))) -NoDesktop`). If that
  step fails, the installer warns and finishes the normal install.
- **Settings → Startup → Start at login** now appears on macOS, Windows and
  Linux (it was macOS only, labelled "Open at login").

**Fixed**
- A tray started at login now finds ffmpeg and Deno. Login items used to get
  a minimal PATH, so transcriptions started from the tray could fail with
  "ffmpeg not found" while the terminal worked.
- `anyscribe tray` runs on Windows (it used to crash on start).
- Starting a second `anyscribe tray` while one is running now exits
  successfully instead of with an error, so a login item doesn't keep
  retrying it.

**Changed**
- `anyscribe install-service` and `uninstall-service` work on Windows and
  Linux as well as macOS. `install-service` refuses until the tray extra is
  installed (`pip install "anyscribe[tray]"`). Removing the login item never
  stops a tray that is already running; quit it from its menu, or run
  `anyscribe desktop uninstall`.

**Upgrading:** after `pip install --upgrade "anyscribe[tray]"`, run
`anyscribe desktop install` once to get the app and the new login item.
Already using start-at-login from an older version? Running it replaces the
old login item with the fixed one.

## 0.17.1 — 2026-10-22

**Changed**
- YouTube downloads now use a JavaScript runtime. YouTube makes downloaders
  solve a small JavaScript puzzle before handing over media; yt-dlp ships the
  solver (`yt-dlp[default]`) and runs it on Deno or Node 22+. anyscribe finds
  whichever you have (including a Deno installed by its own script, before you
  open a new terminal) and tells yt-dlp to use it. With neither, YouTube
  downloads print one warning and still run, but may miss formats or fail.
- The installers offer Deno when neither Deno 2.3+ nor Node 22+ is usable:
  Homebrew on macOS, Deno's install script (into `~/.deno`) on Linux, or
  winget on Windows when available. On apt-based Linux, after you accept
  Deno installation, the installer first attempts to install unzip if it is
  missing. Declining only warns.
- `anyscribe doctor` has a "JavaScript runtime" row.
- Upgrading does not install a runtime. Run `anyscribe doctor`: if the
  "JavaScript runtime" row says Missing, install Deno (`brew install deno` on
  macOS, `winget install DenoLand.Deno` on Windows, Linux steps in
  Troubleshooting) or re-run the one-line installer. If you already have Node
  22 or newer, nothing to do.

**Fixed**
- yt-dlp's auto-update messages no longer appear in `--json` output; they go
  to stderr.
- The Linux installer now asks for your distribution's own Python first when
  it cannot find Python 3.11 or newer, and only then for python3.11 by name
  (Ubuntu 24.04 has no `python3.11` package, so the installer used to stop
  there).

## 0.17.0 — 2026-10-22

**Breaking**
- anyscribe now needs Python 3.11 or newer (Python 3.10 reached end of life
  in October 2026). If you installed with pip or the one-line installer,
  nothing breaks on 3.10: `anyscribe update` and `pip install --upgrade
  anyscribe` keep you on 0.16.5 and report it as up to date. To move to
  0.17.0, re-run the one-line installer from the getting-started guide: it
  finds or installs Python 3.11 or newer and installs anyscribe with it. Then
  run `anyscribe --version`. If it still says 0.16.5, an older copy comes
  first on your PATH: remove it with `python3.10 -m pip uninstall anyscribe`
  (Windows: `py -3.10 -m pip uninstall anyscribe`) and open a new terminal.
  Your settings and transcripts stay where they are. Optional add-ons stay
  with the old Python: if you use offline transcription, run
  `anyscribe local setup --model <size> --yes` again (downloaded models stay
  on disk); if you use the MCP server, install `anyscribe[mcp]` again with
  the new Python.

**Changed**
- anyscribe now requires Starlette 1.3.1 or newer (the web framework under
  the web UI), the first version clear of its published security advisories,
  and FastAPI 0.133 or newer so the two install together. Fresh installs
  already got these; upgrading brings older installs up to them.
- Installers say `anyscribe` everywhere (they still said `scribe`) and no
  longer print "ready" when the post-install step was skipped. The macOS and
  Linux installer routes a Python that has no pip through pipx, using that
  same Python, and asks Python for the real scripts folder in the PATH hint.
- Dependency pins: beaupy is capped below 4 (4.0 makes Ctrl+C in onboarding
  raise instead of taking the default); python-multipart's floor is 0.0.31.
  Python 3.14 is now supported and tested.
- Web UI bundle rebuilt with refreshed frontend dependencies (0 open npm
  advisories at the time of the audit, was 11).

**Fixed**
- The bundled Claude Code skill was corrected against the CLI: wrong flags,
  JSON shapes, provider routing and chunk sizes, dozens of corrections. After
  upgrading, running a normal command such as `anyscribe ui` updates the
  skill Claude Code uses; `anyscribe --version`, `--help` and
  `anyscribe migrate --dry-run` do not. To update it straight away, run
  `anyscribe install-skill --force`.
- The CLI's own help and error text: `anyscribe model info` names the right
  repository for the turbo model; the Groq and OpenAI "no speaker labels"
  errors say exactly how to retry; the hint to paste a URL interactively now
  says `anyscribe transcribe`, not bare `anyscribe`.
- README, user guide and landing page: dozens of corrections (version
  strings, the `--json` output shape, `anyscribe transcribe --clipboard` where
  the docs showed `anyscribe --clipboard`, which errors, local setup flags,
  Sarvam's 28 s chunks, Deepgram's chunking, ElevenLabs' segment timestamps).

## 0.16.5 — 2026-09-13

- anyscribe now uses GNU AGPLv3 or later. Modified versions offered over a network
  must offer corresponding source to their users under the license terms.
  Commercial use remains permitted; earlier MIT releases keep their permissions.
- Source archives include the editable web UI and build files. Bundled frontend
  dependency notices are included in the package.
- Standalone Claude skill installs include the full license and copyright notice;
  reference files retain their UTF-8 text on Windows.

## 0.16.4 — 2026-08-09

**Fixed**
- `pip install anyscribe` no longer prints `WARNING: typer 0.27.1 does not
  provide the extra 'all'`. We were asking for a `typer` extra that typer
  removed; plain `typer` has bundled the same pieces since 0.12. Cosmetic only —
  nothing behaved differently.

**Added**
- This changelog. CI now fails if a version is tagged without an entry here, so
  it can't silently fall behind.

## 0.16.3 — 2026-08-09

**Fixed — affects the MCP server only**
- `anyscribe-mcp` failed to start on any machine that installed it fresh on or
  after 2026-07-28, with `ModuleNotFoundError: No module named
  'mcp.server.fastmcp'`. The MCP library released a version 2 that renamed the
  piece we imported, and we hadn't pinned a version range, so new installs
  picked up the incompatible one. **If you hit this, `pip install -U
  "anyscribe[mcp]"` fixes it.** Existing installs were unaffected.

**Changed**
- The MCP server now speaks protocol revision `2026-07-28`, the current spec.
- Hosts (Claude Desktop, Cursor) now show the server as `anyscribe` with its
  version, instead of the old `scribe` name and a blank version. Resource
  addresses (`scribe://config` and friends) are unchanged, so nothing that
  referenced them breaks.

## 0.16.2 — 2026-08-09

**Changed**
- Every message anyscribe prints now says `anyscribe`, matching the docs.
  `scribe` and `ascli` remain permanent aliases you can keep typing.
- `sarvam` is accepted anywhere a provider name is entered, as a spelling of
  `sargam`. Previously some surfaces silently reported a keyless provider as
  configured.
- `anyscribe ui` now tries the next port (up to 10) when yours is busy instead
  of failing.

## 0.16.1 — 2026-08-09

**Added**
- Rebuilt user documentation as three routes: using anyscribe through an AI
  agent, through the web dashboard, or through the terminal. New agents guide,
  a getting-started that leads with the installer, a separate troubleshooting
  page, and an honest cost-to-start table per provider.
- macOS "open at login" toggle for the menu-bar tray.

**Fixed**
- `install.sh` on fresh Apple Silicon Macs; both installers now include the tray
  extra. The web UI's "setup needed" banner no longer sticks when your only
  configured provider is local.

## 0.16.0 — 2026-07-31

**Changed — action may be needed**
- The project is now `anyscribe`, not `anyscribecli`. The command is
  `anyscribe`; **`scribe` and `ascli` keep working permanently.** Config moved
  from `~/.anyscribecli/` to `~/.anyscribe/` automatically. If anything looks
  missing after upgrading, run `anyscribe migrate` once.

## 0.15.1 — 2026-07-29

**Added**
- The Settings page shows a "Next run" banner telling you exactly which provider
  and model your next transcription will use.
- Provider and model controls are always visible (they used to be hidden until
  you picked "custom"), plus a new Downloads & media section.

## 0.15.0 — 2026-07-29

**Changed**
- Picking a provider now sticks. Previously the quality preset could silently
  override your choice.
- Every run prints the provider and model it chose, and why.
- A quality tier that needs a key you don't have now warns instead of quietly
  falling back to something else.
- `anyscribe config` with no arguments is now a defaults dashboard.
- OpenAI defaults to `gpt-transcribe`, switching to `whisper-1` automatically
  when you ask for timestamps or speaker labels.

**Removed**
- The `OPENROUTER_MODEL` environment variable — set the model in config instead.

## 0.14.1 — 2026-07-29

**Fixed**
- Several transcription bugs from 0.14.0: a malformed language field in
  frontmatter, a crash on an empty `provider_models:` config block, OpenAI
  speaker labels, and Sarvam speaker labels (not supported upstream — now says
  so). Turbo local models pulled during the brief 0.14.0 window need
  re-downloading.

## 0.14.0 — 2026-07-29

**Added**
- Pick the model per provider, not just the provider: `--model/-m` on
  `transcribe` and `batch`, dropdowns in the web UI.

**Changed**
- Refreshed every provider's model list against what each service actually
  offers. OpenRouter's old default had been removed upstream and was silently
  broken.

## 0.13.4 — 2026-07-16

**Fixed**
- Audio files over 25 MB but under 18 minutes no longer lose the original file.
- Groq's API key was not detected in pre-flight checks.

## 0.13.3 — 2026-07-14

**Added**
- Remove a saved provider API key from the web UI (Settings → Providers), with
  a two-step confirm. The secrets file is now created private to your user.

## 0.13.2 — 2026-07-04

**Fixed**
- The menu-bar tray icon was invisible in 0.13.1.

## 0.13.1 — 2026-07-04

**Changed**
- Real tray icon and landing-page copy pass. *Contains the invisible-icon
  regression fixed in 0.13.2 — skip straight to 0.13.2.*

## 0.13.0 — 2026-07-04

**Added**
- Menu-bar tray companion that keeps the web UI running, with start-at-login.

## 0.12.0 — 2026-07-04

**Added**
- `anyscribe logs`, a `--timeout` for batch runs, and live download progress for
  local model downloads in the web UI.

## 0.11.0 — 2026-07-03

**Added**
- Duplicate detection — re-transcribing the same source returns the existing
  file unless you pass `--force`.
- Delete a transcript from any surface (`anyscribe rm`, web UI, MCP).
- Cancel and retry buttons in the web UI.

## 0.10.1 — 2026-06-29

**Fixed**
- Sarvam rejected exactly-30-second audio chunks.

## 0.10.0 — 2026-06-29

**Changed**
- Instagram downloads moved to yt-dlp with browser-cookie authentication.

## 0.9.0 — 2026-06-29

**Added**
- Quality picker — choose accuracy, balanced, cost, or free and let anyscribe
  route to the right provider. Groq added as a provider.

## 0.8.4 — 2026-05-28

**Fixed**
- Release hardening, Windows file-locking issues, pre-flight check fixes.

## 0.8.2 — 2026-04-20

**Fixed**
- The web UI's "Browse local file" no longer submits the moment you pick a file,
  so you can set options first.

## 0.8.1 — 2026-04-18

**Added**
- First-run setup wizard in the web UI, and `anyscribe onboard --yes` for
  agents and scripts — the same setup available three ways.
- Local (offline) transcription: opt-in setup and model management.

## 0.7.4 – 0.7.4.7.2 — 2026-04-18

**Added**
- The web UI itself (`anyscribe ui`): a local dashboard for transcribing and
  configuring, followed by a rapid series of usability fixes — inline API key
  setup, retry and checkpoints, pre-flight checks, cross-platform install
  scripts, a shutdown button, file upload, and a per-provider language picker.

## 0.7.0 – 0.7.2.3 — 2026-04-16

**Added**
- Speaker labels (diarization) and the Deepgram provider. Setting API keys via
  `config set`. Asking for speaker labels routes to Deepgram automatically.

## 0.6.0 — 2026-04-05

**Added**
- The MCP server, so Claude Desktop, Cursor, and other MCP hosts can use
  anyscribe directly.

## 0.5.0 – 0.5.4 — 2026-03-30 → 2026-04-01

**Added**
- Configurable workspace path, Windows support, and automatic yt-dlp updates
  when it goes stale.

## 0.4.0 – 0.4.1 — 2026-03-30

**Added**
- Local file transcription, and the Claude Code skill that installs itself.

## 0.3.0 – 0.3.1 — 2026-03-27 → 2026-03-29

**Added**
- The `download` command. First PyPI release.

## 0.2.0 — 2026-03-26

**Added**
- Instagram, all remaining providers, batch mode, config, and onboarding.

## 0.1.0 — 2026-03-26

**Added**
- First release: YouTube video → markdown transcript via OpenAI.
