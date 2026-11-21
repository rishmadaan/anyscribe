// The old browser launcher from `anyscribe desktop install` (bridge oldLauncher.*): its three
// pieces, and removing them with today's `anyscribe desktop uninstall --json`, then checking each
// piece ourselves. Node only; tested in test/old-launcher.test.js with a throwaway HOME.
'use strict';

const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { runCapture, lastLine } = require('./run');

// core/tray.py's command_line_is(cmdline, "tray"): `python -m anyscribe tray`, or a console
// script under any of its three names. A pid on its own proves nothing (it can be reused).
const TRAY_COMMAND = /(?:-m\s+anyscribe|[\\/](?:anyscribe|scribe|ascli)(?:\.exe)?"?)\s+tray\b/;

function files(home) {
  return {
    launcher: path.join(home, 'Applications', 'anyscribe.app'),
    loginItem: path.join(home, 'Library', 'LaunchAgents', 'com.anyscribe.tray.plist'),
    pidFile: path.join(home, '.anyscribe', 'tray.pid'),
  };
}

// The ports `desktop uninstall` reads, the engine's way (core/desktop.py at b22df16):
// installed_port() is the manifest's port, else the login item's last ProgramArguments entry;
// with neither it uses tray.DEFAULT_PORT.
const ENGINE_DEFAULT_PORT = 8457;

function manifestPort(home) {
  try {
    const m = JSON.parse(fs.readFileSync(path.join(home, '.anyscribe', 'desktop.json'), 'utf8'));
    // Python reads an empty manifest as none.
    if (!m || typeof m !== 'object' || !Object.keys(m).length) return undefined;
    return Number.isInteger(m.port) ? m.port : null;
  } catch {
    return undefined; // no manifest (or unreadable): the engine falls back to the login item
  }
}

// Reading the login item's ProgramArguments exactly, as Python's plistlib does (XML or binary):
// macOS's own plutil. A seam, so tests can stand in for it off a Mac. Returns its JSON text, or
// null where plutil is not there.
const readers = {
  plutil: (file) =>
    process.platform === 'darwin'
      ? execFileSync('/usr/bin/plutil', ['-extract', 'ProgramArguments', 'json', '-o', '-', file], { timeout: 5000 }).toString()
      : null,
};

function programArguments(file) {
  try {
    const args = JSON.parse(readers.plutil(file));
    if (Array.isArray(args)) return args.map(String);
  } catch {
    // plutil missing or failed: the XML read below
  }
  try {
    const xml = fs.readFileSync(file, 'utf8');
    const body = xml.match(/<key>ProgramArguments<\/key>\s*<array>([\s\S]*?)<\/array>/)[1];
    return [...body.matchAll(/<string>([^<]*)<\/string>/g)].map((m) => m[1]);
  } catch {
    return null; // unknown
  }
}

// The login item's port: its last argument, as the engine reads it.
function loginItemPort(home) {
  const port = Number(programArguments(files(home).loginItem)?.at(-1));
  return Number.isInteger(port) ? port : null;
}

// The port `desktop uninstall` would stop a server on.
function uninstallTarget(home) {
  const m = manifestPort(home);
  if (m !== undefined) return m ?? ENGINE_DEFAULT_PORT;
  return loginItemPort(home) ?? ENGINE_DEFAULT_PORT;
}

// The ports a live old tray could serve, from its own command line (its teardown posts a
// shutdown there, whatever the files say now). Conservative rather than a copy of Click's rules:
// every port the line names after `tray`, in every form Click accepts (--port N, --port=N, -p N,
// -pN, repeated), else the tray's default 8457. null when no live tray; readable: false (and
// 8457 added) when a named port does not parse.
async function trayPort(home, cmdline = commandLine) {
  const line = await liveTrayCommand(home, cmdline);
  if (line == null) return null;
  const args = line.slice(line.search(/\stray\b/) + 1);
  const named = [...args.matchAll(/(?:^|\s)(?:--port(?:=|\s+)|-p\s*)(\S+)/g)].map((m) => Number(m[1]));
  const ports = named.filter(Number.isInteger);
  const readable = ports.length === named.length;
  return { ports: ports.length && readable ? ports : [...ports, ENGINE_DEFAULT_PORT], readable };
}

// Every port the old launcher records or a live old tray serves: the app never chooses one.
// note(message): a live tray whose port could not be read (8457 is avoided; the start goes ahead).
async function recordedPorts(home, { note = () => {}, cmdline } = {}) {
  const tray = await trayPort(home, cmdline);
  if (tray && !tray.readable) note("the old menu bar icon's port couldn't be read from its command line; avoiding 8457");
  return [manifestPort(home), loginItemPort(home), ENGINE_DEFAULT_PORT, ...(tray?.ports ?? [])].filter(Number.isInteger);
}

function lexists(p) {
  try {
    fs.lstatSync(p);
    return true;
  } catch {
    return false;
  }
}

// The command line of a pid: /proc on Linux (never truncated), else `ps -ww`.
async function commandLine(pid) {
  if (process.platform === 'linux') {
    try {
      return fs.readFileSync(`/proc/${pid}/cmdline`).toString().replace(/\0/g, ' ');
    } catch {
      return '';
    }
  }
  const r = await runCapture('ps', ['-ww', '-o', 'command=', '-p', String(pid)], { env: { PATH: '/bin:/usr/bin' }, timeoutMs: 5000 });
  return r.out;
}

// The old menu bar icon: tray.pid names a live process that is an anyscribe tray.
// The live old tray's command line, or null (no tray.pid, a dead pid, or not a tray).
async function liveTrayCommand(home, cmdline = commandLine) {
  let pid;
  try {
    pid = Number.parseInt(fs.readFileSync(files(home).pidFile, 'utf8').trim(), 10);
  } catch {
    return null;
  }
  if (!(pid > 0)) return null;
  try {
    process.kill(pid, 0);
  } catch (err) {
    if (err.code !== 'EPERM') return null; // EPERM: alive, someone else's
  }
  const line = await cmdline(pid);
  return TRAY_COMMAND.test(line) ? line : null;
}

async function trayRunning(home, cmdline = commandLine) {
  return (await liveTrayCommand(home, cmdline)) != null;
}

async function pieces(home, cmdline) {
  const f = files(home);
  return {
    launcher: lexists(f.launcher) ? 'present' : 'absent',
    loginItem: lexists(f.loginItem) ? 'present' : 'absent',
    menuBarIcon: (await trayRunning(home, cmdline)) ? 'running' : 'not running',
  };
}

// Works on any OS; only a Mac can have it installed (elsewhere `installed` is false). Any piece
// left, a live old tray alone included, counts: that is when cleanup is still needed (C6).
async function status({ home, platform, cmdline }) {
  const p = await pieces(home, cmdline);
  const left = p.launcher === 'present' || p.loginItem === 'present' || p.menuBarIcon === 'running';
  return { ok: true, installed: platform === 'darwin' && left, pieces: p };
}

const ONLY_MAC = { ok: false, reason: 'The old launcher is removed only on a Mac.', pieces: null, startAtLoginCarriedOver: false };

// The uninstall step. ctx: {home, platform, python, pythonError, env (the engine's),
// setStartAtLogin, loginItemState (the system's: "enabled", "requires-approval", ...), cmdline?,
// run?}. ok only when all three pieces are gone. When the old login item was there and is now
// gone, the app's own Start at login is turned on in its place. Run it only through
// removePausingEngine: the uninstall can stop this app's engine.
async function remove({ home, platform, python, pythonError, env, setStartAtLogin, loginItemState, cmdline, run = runCapture }) {
  if (platform !== 'darwin') return ONLY_MAC;
  const before = await pieces(home, cmdline);
  const r = python
    ? await run(python, ['-m', 'anyscribe', 'desktop', 'uninstall', '--json'], { env, cwd: home, timeoutMs: 60_000, helper: true })
    : { code: null, error: new Error(pythonError || "anyscribe's engine couldn't be found") };
  const after = await pieces(home, cmdline);
  const result = {
    launcher: after.launcher === 'absent' ? 'removed' : 'still there',
    loginItem: after.loginItem === 'absent' ? 'removed' : 'still there',
    menuBarIcon: after.menuBarIcon === 'not running' ? 'stopped' : 'still running',
  };
  let startAtLoginCarriedOver = false;
  let loginNote = null;
  if (before.loginItem === 'present' && after.loginItem === 'absent') {
    setStartAtLogin(true);
    // Carried over only when the system says so (C5); macOS can hold it for approval.
    const state = loginItemState();
    if (state === 'enabled') startAtLoginCarriedOver = true;
    else if (state === 'requires-approval') loginNote = 'This app is set to start at login, but macOS needs your approval: System Settings, General, Login Items.';
    else loginNote = `This app couldn't be set to start at login (macOS says: ${state}).`;
  }
  const ok = result.launcher === 'removed' && result.loginItem === 'removed' && result.menuBarIcon === 'stopped';
  if (ok) return { ok, ...(loginNote ? { reason: loginNote } : {}), pieces: result, startAtLoginCarriedOver };
  const left = [
    result.launcher !== 'removed' && 'the launcher is still in ~/Applications',
    result.loginItem !== 'removed' && 'its login item is still there',
    result.menuBarIcon !== 'stopped' && 'the old menu bar icon is still running',
  ].filter(Boolean);
  const failed = r.code !== 0 ? ` The uninstall said: ${r.error?.message || lastLine(r.err) || lastLine(r.out) || (r.timedOut ? 'it took longer than a minute' : `exit ${r.code}`)}.` : '';
  return { ok, reason: [`Cleanup didn't finish: ${left.join(', ')}.${failed}`, loginNote].filter(Boolean).join(' '), pieces: result, startAtLoginCarriedOver };
}

// Removal pauses the app's engine (round 3 design). `desktop uninstall` stops whatever anyscribe
// answers on the old launcher's port and whatever its server.pid names, and either can be this
// app's engine; no check of ours can tell them apart. So the uninstall runs inside
// engine.restart(), after the engine and its group have exited and before it is spawned again.
// restart() refuses (running, waiting or unknown transcriptions; a restart under way) and then
// nothing runs. onResult(result) is called before the engine comes back, so a reloaded dashboard
// finds it.
async function removePausingEngine(engine, ctx, onResult = () => {}) {
  if (ctx.platform !== 'darwin') return ONLY_MAC;
  let result = null;
  let step = null; // the uninstall step, once restart() reached it
  const restarted = await engine.restart({
    between: () =>
      (step = (async () => {
        try {
          result = await remove(ctx);
        } catch (err) {
          result = { ok: false, reason: `The removal failed: ${err.message}`, pieces: null, startAtLoginCarriedOver: false };
        }
        onResult(result);
      })()),
  });
  await step; // a stop or quit during the step ends the restart early; the step still finishes
  if (!result) return { ok: false, reason: restarted.reason, pieces: null, startAtLoginCarriedOver: false };
  if (restarted.ok) return result;
  const note = `anyscribe's engine didn't start again afterwards: ${restarted.reason}`;
  const final = { ...result, reason: [result.reason, note].filter(Boolean).join(' ') };
  onResult(final);
  return final;
}

module.exports = { TRAY_COMMAND, ENGINE_DEFAULT_PORT, readers, files, manifestPort, loginItemPort, uninstallTarget, recordedPorts, trayPort, trayRunning, pieces, status, remove, removePausingEngine };
