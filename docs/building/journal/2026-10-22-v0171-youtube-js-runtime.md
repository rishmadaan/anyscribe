---
type: decision
tags: [youtube, yt-dlp, deno, node, installers, dependencies]
tldr: "v0.17.1 gives yt-dlp a JavaScript runtime for YouTube: yt-dlp[default] ships the challenge solver, core/deps.py finds Deno or Node 22+ and passes --js-runtimes, doctor shows a runtime row, and the installers add Deno when neither runtime exists. Owner chose this over a warning-only option on reliability grounds."
---

# v0.17.1: a JavaScript runtime for YouTube

## The problem

YouTube makes downloaders solve a small JavaScript challenge before it serves
media. yt-dlp moved that solving into a companion package, `yt-dlp-ejs`
(in the `default` extra since 2025.11.12), whose scripts need a runtime: Deno
(enabled by default, minimum 2.3), or Node 22+ behind `--js-runtimes node`.
Verified on this Mac with Deno hidden from PATH: yt-dlp still downloaded but
warned "No supported JavaScript runtime could be found... some formats may be
missing". Degraded, not broken, and at YouTube's mercy.

## Options put to the owner, 2026-10-22

(a) document it; (b) `yt-dlp[default]` plus a doctor warning; (c) also
install a runtime. The owner chose (c): "I'd go with reliable and stable
functionality over a shortcut". A warning the user cannot act on from inside
anyscribe is not reliability.

## What shipped

- `yt-dlp[default]>=2025.11.12`.
- `core/deps.py::find_js_runtime` looks for deno on PATH, then
  `~/.deno/bin/deno` (Deno's install script puts it there and only a new shell
  sees it on PATH), then node. `js_runtime_args` returns
  `--js-runtimes <name>:<path>`, so yt-dlp uses exactly that binary; node is
  not enabled by yt-dlp unless named. `warn_if_no_js_runtime` prints once per
  process. The YouTube downloader and `cli/download.py::_download_video` (YouTube
  video downloads) pass the flag; Instagram does not need it and keeps its
  exact old command.
- Warnings and yt-dlp's auto-update messages go to stderr, so `--json` output
  and the MCP stdio server stay clean; the 60-day auto-update upgrades
  `yt-dlp[default]`, keeping `yt-dlp-ejs` in step; `/api/health` `ok` counts
  required dependencies only.
- The Linux installer asks for the distribution's own python3 first whenever
  it cannot find Python 3.11 or newer (Ubuntu 24.04 has no `python3.11`
  package, found in Docker) and only then for python3.11 by name.
- `anyscribe doctor`: an optional "JavaScript runtime" row showing the
  detected runtime and version, or `Missing (optional)` with a description of
  the dependency. Each candidate is run with `--version` and skipped when it is
  not what its name says or is below yt-dlp's minimum (Deno 2.3, Node 22).
- Installers: accept Deno or Node 22+ (Node is already on many machines, so no
  second runtime is forced); otherwise offer Deno via Homebrew, Deno's script
  with `--yes` (installs to `~/.deno`, needs unzip), or winget. Declining only
  warns.
- Flag syntax checked live: `--js-runtimes deno:/opt/homebrew/bin/deno` and
  `--js-runtimes node:<path>` both fetched metadata for a public video with no
  runtime warning.

## Exit

Uninstall Deno and yt-dlp degrades to the warned behaviour; Node is a drop-in
replacement. No account, service, or data format is involved.
