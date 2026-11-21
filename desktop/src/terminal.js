// "Use from Terminal and Claude Code" (bridge terminal.*): our command at ~/.local/bin/anyscribe,
// what Terminal actually runs, and the Claude Code skill. Node only (no Electron), so
// test/terminal.test.js drives it with a throwaway HOME.
//
// ctx: {home, shell, python, pythonError, env (the engine's environment), appVersion, packaged,
// resourcesPath, execPath}.
'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { runCapture, lastLine } = require('./run');

const MARKER = 'anyscribe-mac-app-command';
const PATH_LINE = 'export PATH="$HOME/.local/bin:$PATH"';
const SHELL_TIMEOUT_MS = 5000;
const SKILL_TIMEOUT_MS = 60_000;

const sha256 = (text) => crypto.createHash('sha256').update(text).digest('hex');
const shq = (s) => `'${String(s).replace(/'/g, "'\\''")}'`;

function files(home) {
  const runtime = path.join(home, '.anyscribe', 'runtime');
  return {
    bin: path.join(home, '.local', 'bin'),
    command: path.join(home, '.local', 'bin', 'anyscribe'),
    record: path.join(runtime, 'terminal.json'),
    backup: path.join(runtime, 'replaced', 'anyscribe'),
    claude: path.join(home, '.claude'),
    skill: path.join(home, '.claude', 'skills', 'anyscribe'),
  };
}

const exists = (p) => fs.existsSync(p);
// True for a dangling symlink too (existsSync follows links).
function lexists(p) {
  try {
    fs.lstatSync(p);
    return true;
  } catch {
    return false;
  }
}

// The command: the engine's environment (engine review F2: without it `anyscribe update` and
// local setup would write into the signed app), then the app's Python.
function commandScript({ appVersion, python, packaged, resourcesPath, execPath }) {
  const lines = [
    '#!/bin/sh',
    `# ${MARKER} ${appVersion}: the anyscribe Mac app's Terminal command. Turning off "Use from Terminal" in the app's Settings removes it.`,
    'export ANYSCRIBE_APP=1',
    'export PIP_USER=1',
    'export PYTHONUSERBASE="$HOME/.anyscribe/runtime"',
  ];
  if (packaged) {
    lines.push(`export PATH=${shq(path.join(resourcesPath, 'bin'))}:"$PATH"`);
    lines.push(`export ANYSCRIBE_ELECTRON=${shq(execPath)}`);
  }
  lines.push(`exec ${shq(python)} -m anyscribe "$@"`, '');
  return lines.join('\n');
}

// ~/.anyscribe/runtime/terminal.json: {command, sha256, previousSha256, appVersion, replaced, skillError}.
function readRecord(f) {
  try {
    const rec = JSON.parse(fs.readFileSync(f.record, 'utf8'));
    return rec && typeof rec === 'object' ? rec : {};
  } catch {
    return {};
  }
}

// A fresh temp file beside `target`, created exclusively ('wx'): an existing file or symlink at
// that name is never written through or removed. Tests replace naming.tempTag to plant one.
const naming = { tempTag: () => crypto.randomBytes(6).toString('hex') };
function writeTemp(target, data, mode) {
  const tmp = path.join(path.dirname(target), `.${path.basename(target)}.${naming.tempTag()}.tmp`);
  const fd = fs.openSync(tmp, 'wx', mode);
  let written = false;
  try {
    fs.writeFileSync(fd, data);
    fs.fchmodSync(fd, mode);
    written = true;
  } finally {
    fs.closeSync(fd);
    if (!written) fs.rmSync(tmp, { force: true }); // ours: this call created it
  }
  return tmp;
}

function writeRecord(f, rec) {
  fs.mkdirSync(path.dirname(f.record), { recursive: true });
  const tmp = writeTemp(f.record, `${JSON.stringify(rec, null, 2)}\n`, 0o644);
  try {
    fs.renameSync(tmp, f.record);
  } catch (err) {
    fs.rmSync(tmp, { force: true });
    throw err;
  }
}

// Ours: a regular file whose second line is our marker and whose content hash is one the record
// accepts: the new one, or the one it replaces (a write is committed by the record before the
// file moves, so ours stays ours at every step). A symlink, an edited copy or a copy we never
// recorded is not ours.
function isOurs(f, rec) {
  if (!rec.sha256) return false;
  try {
    if (!fs.lstatSync(f.command).isFile()) return false;
    const text = fs.readFileSync(f.command, 'utf8');
    return text.split('\n')[1]?.startsWith(`# ${MARKER} `) === true && [rec.sha256, rec.previousSha256].includes(sha256(text));
  } catch {
    return false;
  }
}

// What a file was, for the record: a symlink's target, or a file's content hash.
function describe(p) {
  const st = fs.lstatSync(p);
  if (st.isSymbolicLink()) return { kind: 'symlink', target: fs.readlinkSync(p) };
  if (st.isFile()) return { kind: 'file', sha256: sha256(fs.readFileSync(p)), mode: st.mode & 0o7777 };
  return { kind: 'other' };
}

// ---- asking the login shell what Terminal runs ----

function shellEnv(ctx) {
  const user = os.userInfo().username;
  // What a new Terminal window starts from (launchd's PATH); the profile files do the rest.
  return { HOME: ctx.home, USER: user, LOGNAME: user, SHELL: ctx.shell, PATH: '/usr/bin:/bin:/usr/sbin:/sbin', LANG: 'en_US.UTF-8', TERM: 'dumb' };
}

function shellScript(token) {
  const m = (name) => `__anyscribe_${token}_${name}__`;
  return {
    script: `printf '\\n%s\\n' ${m('begin')}; command -v anyscribe; printf '\\n%s\\n%s\\n%s\\n' ${m('path')} "$PATH" ${m('end')}`,
    markers: { begin: m('begin'), path: m('path'), end: m('end') },
  };
}

// The text between our markers, whatever the rc files printed around it. null when the markers
// are not all there (the shell failed or timed out before the end).
function parseShellOutput(out, markers) {
  const b = out.indexOf(`${markers.begin}\n`);
  const p = out.indexOf(`\n${markers.path}\n`, b);
  const e = out.indexOf(`\n${markers.end}`, p + 1);
  if (b < 0 || p < 0 || e < 0) return null;
  const found = lastLine(out.slice(b + markers.begin.length + 1, p));
  const pathText = out.slice(p + markers.path.length + 2, e).trim();
  return { found, pathDirs: pathText ? pathText.split(':') : [] };
}

// {ok: true, found: path | alias text | null, pathDirs} or {ok: false, reason}.
async function askLoginShell(ctx) {
  if (!ctx.shell) return { ok: false, reason: "anyscribe couldn't tell which shell Terminal uses." };
  const { script, markers } = shellScript(crypto.randomBytes(8).toString('hex'));
  const r = await runCapture(ctx.shell, ['-lic', script], {
    env: shellEnv(ctx),
    cwd: ctx.home,
    timeoutMs: ctx.shellTimeoutMs ?? SHELL_TIMEOUT_MS,
    until: `\n${markers.end}\n`,
  });
  const parsed = parseShellOutput(r.out, markers);
  if (parsed) return { ok: true, ...parsed };
  const why = r.error ? r.error.message : r.timedOut ? 'it took longer than 5 seconds' : `it exited with ${r.signal ?? `code ${r.code}`}`;
  return { ok: false, reason: `anyscribe couldn't ask your Terminal's shell (${path.basename(ctx.shell)}) which anyscribe it runs: ${why}.` };
}

// How another copy was installed, from where its file really lives.
function viaOf(p) {
  let real = p;
  try {
    real = fs.realpathSync(p);
  } catch {
    // a dangling link: judge by the path itself
  }
  if (/[\\/]uv[\\/]tools[\\/]/.test(real)) return 'uv';
  if (/[\\/]pipx[\\/]venvs[\\/]/.test(real)) return 'pipx';
  try {
    if (/^#!.*python/.test(fs.readFileSync(real).subarray(0, 256).toString())) return 'pip';
  } catch {
    // unreadable
  }
  return 'unknown';
}

async function versionOf(p, ctx) {
  const r = await runCapture(p, ['--version'], { env: shellEnv(ctx), cwd: ctx.home, timeoutMs: ctx.shellTimeoutMs ?? SHELL_TIMEOUT_MS });
  return r.out.match(/\d+\.\d+\.\d+[\w.+-]*/)?.[0] ?? null;
}

function samePath(a, b) {
  try {
    return fs.realpathSync(a) === fs.realpathSync(b);
  } catch {
    return path.resolve(a) === path.resolve(b);
  }
}

// off: no command of ours. on: Terminal runs ours (or ours is written and the shell could not be
// asked; the reason says so). other-copy: Terminal runs a different anyscribe first.
// path-missing: ours is written but the login shell finds no anyscribe.
function terminalState({ ours, shellKnown, foundOurs, foundOther }) {
  if (foundOther) return 'other-copy';
  if (!ours) return 'off';
  if (foundOurs || !shellKnown) return 'on';
  return 'path-missing';
}

// "installed" only when the latest install attempt succeeded (or none was needed): an older
// SKILL.md left behind by a failed --force install does not count (C3).
function skillState(f, rec) {
  if (!exists(f.claude)) return 'not-applicable';
  if (rec.skillError) return 'missing';
  return exists(path.join(f.skill, 'SKILL.md')) ? 'installed' : 'missing';
}

// sh: an askLoginShell answer already in hand, so one call does not ask twice.
async function status(ctx, sh = null) {
  const f = files(ctx.home);
  const rec = readRecord(f);
  const ours = isOurs(f, rec);
  sh ??= await askLoginShell(ctx);
  const notes = [];
  let uses = null;
  if (!sh.ok) notes.push(sh.reason);
  else if (sh.found && !sh.found.startsWith('/')) uses = { path: null, version: null, via: 'unknown' }; // an alias or function
  else if (sh.found && ours && samePath(sh.found, f.command)) uses = { path: sh.found, version: ctx.appVersion, via: 'app' };
  else if (sh.found) uses = { path: sh.found, version: await versionOf(sh.found, ctx), via: viaOf(sh.found) };
  if (ours && uses && uses.via !== 'app') {
    notes.push(uses.path ? `Terminal finds another anyscribe at ${uses.path} first.` : 'Terminal finds another anyscribe first (an alias or a shell function).');
  }
  // What sits at ~/.local/bin/anyscribe when it is not ours: the only copy "Switch" can replace (F1).
  let occupant = null;
  if (!ours && lexists(f.command)) {
    occupant = uses?.path && samePath(uses.path, f.command)
      ? { path: f.command, via: uses.via, version: uses.version }
      : { path: f.command, via: viaOf(f.command), version: await versionOf(f.command, ctx) };
  }
  const skill = skillState(f, rec);
  if (skill === 'missing' && rec.skillError) notes.push(rec.skillError);
  return {
    ok: true,
    reason: notes.join(' ') || null,
    state: terminalState({ ours, shellKnown: sh.ok, foundOurs: uses?.via === 'app', foundOther: Boolean(uses) && uses.via !== 'app' }),
    command: ours ? f.command : null,
    uses,
    occupant,
    appVersion: ctx.appVersion,
    claudeCode: exists(f.claude),
    skill,
  };
}

// `install-skill --force` (the engine's command for it): the skill matches the copy Terminal now runs (an older one left by
// another copy would otherwise stay). Records why it failed, for the status.
async function installSkill(ctx, f) {
  const started = Date.now();
  const r = await runCapture(ctx.python, ['-m', 'anyscribe', 'install-skill', '--force'], {
    env: ctx.env,
    cwd: ctx.home,
    timeoutMs: SKILL_TIMEOUT_MS,
  });
  let error = null;
  const line = lastLine(r.err) || lastLine(r.out);
  if (/PermissionError|Permission denied/.test(line || '')) error = "Couldn't write to ~/.claude/skills (permission denied).";
  else if (r.timedOut) error = 'The Claude Code skill install took longer than a minute.';
  else if (r.code !== 0) error = `The Claude Code skill couldn't be installed: ${r.error?.message || line || `exit ${r.code}`}.`;
  else if (!writtenSince(path.join(f.skill, 'SKILL.md'), started)) error = "The Claude Code skill couldn't be installed: install-skill finished without writing it.";
  writeRecord(f, { ...readRecord(f), skillError: error });
  return error;
}

// Written by this attempt (2 s of slack for coarse file times), not left over from an older one.
function writtenSince(p, started) {
  try {
    return fs.statSync(p).mtimeMs >= started - 2000;
  } catch {
    return false;
  }
}

const OTHER_AT_PATH = 'Another anyscribe is already at ~/.local/bin/anyscribe. Keep it, or switch to this app\'s copy (the other one is kept in ~/.anyscribe/runtime/replaced).';

// Writes our command. Never overwrites a file that is not ours unless `replace`; with replace,
// the other file (or symlink) is moved to ~/.anyscribe/runtime/replaced/anyscribe, never deleted.
// ok: false only when the command was not written; the skill's result is in `skill` and `reason`.
async function turnOn(ctx, { replace = false } = {}) {
  const f = files(ctx.home);
  if (!ctx.python) return { ...(await status(ctx)), ok: false, reason: ctx.pythonError || "anyscribe's engine couldn't be found." };
  const rec = readRecord(f);
  const ours = isOurs(f, rec);
  const other = !ours && lexists(f.command);
  if (other && !replace) return { ...(await status(ctx)), ok: false, reason: OTHER_AT_PATH };
  const text = commandScript(ctx);
  let replaced = rec.replaced && lexists(f.backup) ? rec.replaced : null;
  let tmp = null;
  let movedAside = false;
  try {
    fs.mkdirSync(f.bin, { recursive: true });
    tmp = writeTemp(f.command, text, 0o755);
    if (other) replaced = describe(f.command);
    // The record commits the write (round 3): it names the new hash and still accepts the current
    // one, so a record that cannot be saved stops here with the command untouched, and a crash at
    // any later point leaves ours ours.
    writeRecord(f, {
      command: f.command,
      sha256: sha256(text),
      previousSha256: ours ? sha256(fs.readFileSync(f.command, 'utf8')) : null,
      appVersion: ctx.appVersion,
      replaced,
      skillError: null,
    });
    if (other) {
      fs.mkdirSync(path.dirname(f.backup), { recursive: true });
      if (lexists(f.backup)) fs.renameSync(f.backup, `${f.backup}.${Date.now()}`); // an older one, kept too
      fs.renameSync(f.command, f.backup);
      movedAside = true;
    }
    if (ours) {
      fs.renameSync(tmp, f.command);
    } else {
      fs.linkSync(tmp, f.command); // fails if anything appeared there since
      fs.rmSync(tmp, { force: true });
    }
    tmp = null;
  } catch (err) {
    if (tmp) fs.rmSync(tmp, { force: true }); // only the temp this call created
    if (movedAside && !lexists(f.command)) fs.renameSync(f.backup, f.command); // put theirs back
    return { ...(await status(ctx)), ok: false, reason: `Couldn't write ~/.local/bin/anyscribe: ${err.message}` };
  }
  if (exists(f.claude)) await installSkill(ctx, f);
  return { ...(await status(ctx)), ok: true };
}

// Removes ours only if it is still ours; puts back what it replaced only if the path holds exactly
// our file. Otherwise touches nothing and asks (needsChoice), unless there is nothing to put back.
// choice (the answer to that question): 'keep-current' forgets ours and leaves the file there;
// 'restore' moves the current file aside (kept) and puts the replaced one back.
async function turnOff(ctx, { choice = null } = {}) {
  const f = files(ctx.home);
  const rec = readRecord(f);
  if (!rec.sha256) return { ...(await status(ctx)), ok: true }; // nothing of ours was written
  const ours = isOurs(f, rec);
  const hasBackup = Boolean(rec.replaced) && lexists(f.backup);
  let note = null;
  try {
    if (ours) {
      if (hasBackup) fs.renameSync(f.backup, f.command); // replaces ours in one step
      else fs.unlinkSync(f.command);
    } else if (hasBackup) {
      if (choice !== 'keep-current' && choice !== 'restore') {
        const now = lexists(f.command) ? 'has changed' : 'was removed';
        return {
          ...(await status(ctx)),
          ok: false,
          needsChoice: 'keep-current-or-restore',
          reason: `~/.local/bin/anyscribe ${now} since anyscribe put it there. Keep it as it is, or put back the anyscribe it replaced?`,
        };
      }
      if (choice === 'restore') {
        if (lexists(f.command)) fs.renameSync(f.command, `${f.backup}.${Date.now()}`); // kept, never deleted
        fs.renameSync(f.backup, f.command);
      }
    } else if (lexists(f.command)) {
      note = '~/.local/bin/anyscribe was changed since anyscribe wrote it, so it was left as it is.';
    }
    writeRecord(f, {});
  } catch (err) {
    return { ...(await status(ctx)), ok: false, reason: `Couldn't turn it off: ${err.message}` };
  }
  // The skill goes only when Terminal is left with no anyscribe at all.
  const sh = await askLoginShell(ctx);
  if (exists(f.skill)) {
    if (sh.ok && !sh.found) fs.rmSync(f.skill, { recursive: true, force: true });
    else if (!sh.ok) note = [note, 'The Claude Code skill was kept: anyscribe couldn\'t check whether Terminal has another anyscribe.'].filter(Boolean).join(' ');
  }
  const st = await status(ctx, sh);
  return { ...st, ok: true, reason: [note, st.reason].filter(Boolean).join(' ') || null };
}

async function retrySkill(ctx) {
  const f = files(ctx.home);
  if (!exists(f.claude)) return { ...(await status(ctx)), ok: false, reason: "Claude Code isn't on this Mac." };
  if (!ctx.python) return { ...(await status(ctx)), ok: false, reason: ctx.pythonError || "anyscribe's engine couldn't be found." };
  const error = await installSkill(ctx, f);
  const st = await status(ctx);
  return error ? { ...st, ok: false, reason: error } : { ...st, ok: true };
}

// One line in the login shell's own profile file, never twice, never another shell's file.
// Then the login shell is asked again: a later rc file can undo the line (F6).
async function addToPath(ctx) {
  const name = path.basename(ctx.shell || '');
  const line = PATH_LINE;
  const byHand = { ok: false, file: null, line, reason: `Add ~/.local/bin to your shell's PATH by hand: ${line}` };
  let file;
  if (name === 'zsh') {
    file = path.join(ctx.home, '.zprofile');
  } else if (name === 'bash') {
    file = path.join(ctx.home, '.bash_profile');
    // bash reads only the first of these; creating .bash_profile would hide the others.
    const shadowed = ['.bash_login', '.profile'].find((n) => !exists(file) && exists(path.join(ctx.home, n)));
    if (shadowed) return { ...byHand, reason: `Your bash reads ~/${shadowed}; add this line to it by hand: ${line}` };
  } else {
    return byHand;
  }
  try {
    const text = exists(file) ? fs.readFileSync(file, 'utf8') : '';
    if (!text.split('\n').some((l) => l.trim() === line)) {
      fs.appendFileSync(file, `${text && !text.endsWith('\n') ? '\n' : ''}${line}\n`);
    }
  } catch (err) {
    return { ok: false, file, line, reason: `Couldn't add the line to ${file}: ${err.message}` };
  }
  const sh = await askLoginShell(ctx);
  const bin = files(ctx.home).bin;
  if (sh.ok && !sh.pathDirs.some((d) => samePath(d, bin))) {
    const rc = name === 'zsh' ? '~/.zshrc' : '~/.bashrc';
    return { ok: true, file, line, reason: `The line is in ~/${path.basename(file)}, but your shell setup removes it again later (check ${rc}).` };
  }
  return { ok: true, file, line };
}

module.exports = {
  naming,
  MARKER,
  PATH_LINE,
  files,
  commandScript,
  readRecord,
  isOurs,
  parseShellOutput,
  shellScript,
  askLoginShell,
  viaOf,
  terminalState,
  status,
  turnOn,
  turnOff,
  retrySkill,
  addToPath,
};
