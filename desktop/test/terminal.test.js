// "Use from Terminal and Claude Code" (src/terminal.js) against a throwaway HOME: never the real
// ~/.local/bin, shell profiles or ~/.claude. The login shell is the real zsh or bash reading the
// throwaway HOME's (noisy) profile files; the engine's Python is a stand-in shell script.
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const terminal = require('../src/terminal');

const ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'anyscribe-terminal-test-'));
test.after(() => fs.rmSync(ROOT, { recursive: true, force: true }));

// A stand-in for the engine's Python: `-m anyscribe install-skill --force` writes the skill (or
// fails like a permission error with FAKE_SKILL_FAIL=1); `-m anyscribe --version` prints a
// version and the environment the command gave it. Every call is logged.
const FAKE_PYTHON = path.join(ROOT, 'fake-python');
const CALLS = path.join(ROOT, 'calls.log');
fs.writeFileSync(
  FAKE_PYTHON,
  `#!/bin/sh
echo "$*" >> '${CALLS}'
if [ "$3" = install-skill ]; then
  if [ -f "$HOME/skill-noop" ]; then exit 0; fi
  if [ -f "$HOME/skill-fails" ]; then printf '%s\n' "PermissionError: [Errno 13] Permission denied: '$HOME/.claude/skills/anyscribe'" '╰────╯' >&2; exit 1; fi
  mkdir -p "$HOME/.claude/skills/anyscribe" && echo skill > "$HOME/.claude/skills/anyscribe/SKILL.md"
  exit 0
fi
echo "anyscribe v0.20.0 app=$ANYSCRIBE_APP pipuser=$PIP_USER userbase=$PYTHONUSERBASE"
`,
  { mode: 0o755 }
);
const calls = () => (fs.existsSync(CALLS) ? fs.readFileSync(CALLS, 'utf8') : '');

const ZSH = '/usr/bin/zsh';
const BASH = '/bin/bash';

let n = 0;
// A home whose login shell prints noise (before, after, and a line with no newline) and whose
// PATH holds `dirs` (relative to the home) in front of the system's.
function home({ shell = ZSH, dirs = [], claude = false } = {}) {
  const h = path.join(ROOT, `home-${n++}`);
  fs.mkdirSync(h, { recursive: true });
  const pathLine = dirs.length ? `export PATH="${dirs.map((d) => `$HOME/${d}`).join(':')}:$PATH"\n` : '';
  const noise = 'echo "Welcome back, noisy profile"\nprintf "a line with no newline"\n';
  if (shell === ZSH) {
    fs.writeFileSync(path.join(h, '.zprofile'), `${noise}${pathLine}`);
    fs.writeFileSync(path.join(h, '.zshrc'), 'echo "rc noise: anyscribe /usr/bin/anyscribe"\n');
  } else {
    fs.writeFileSync(path.join(h, '.bash_profile'), `${noise}${pathLine}echo "more noise"\n`);
  }
  if (claude) fs.mkdirSync(path.join(h, '.claude'));
  return h;
}

function ctx(h, extra = {}) {
  return {
    home: h,
    shell: ZSH,
    python: FAKE_PYTHON,
    env: { HOME: h, PATH: '/usr/bin:/bin' },
    appVersion: '0.20.0',
    packaged: false,
    ...extra,
  };
}

const cmdPath = (h) => path.join(h, '.local', 'bin', 'anyscribe');
const backupPath = (h) => path.join(h, '.anyscribe', 'runtime', 'replaced', 'anyscribe');
const read = (p) => fs.readFileSync(p, 'utf8');
const record = (h) => JSON.parse(read(path.join(h, '.anyscribe', 'runtime', 'terminal.json')));

// A copy installed with uv: ~/.local/bin/anyscribe is a symlink into uv's tools folder.
function uvCopy(h, version = '0.19.0') {
  const real = path.join(h, '.local', 'share', 'uv', 'tools', 'anyscribe', 'bin', 'anyscribe');
  fs.mkdirSync(path.dirname(real), { recursive: true });
  fs.writeFileSync(real, `#!/bin/sh\necho "anyscribe v${version}"\n`, { mode: 0o755 });
  fs.mkdirSync(path.dirname(cmdPath(h)), { recursive: true });
  fs.symlinkSync(real, cmdPath(h));
  return real;
}

// A copy installed with pip: a regular file whose shebang is a Python.
function pipCopy(h) {
  fs.mkdirSync(path.dirname(cmdPath(h)), { recursive: true });
  fs.writeFileSync(cmdPath(h), '#!/usr/bin/python3\n# pip console script\nimport sys\n', { mode: 0o750 });
}

// ---- the command file ----

test('the command: marker with the version on line 2, the engine environment, then the Python (F2)', () => {
  const dev = terminal.commandScript({ appVersion: '0.20.0', python: "/x/it's python", packaged: false });
  const lines = dev.split('\n');
  assert.equal(lines[0], '#!/bin/sh');
  assert.match(lines[1], /^# anyscribe-mac-app-command 0\.20\.0: /);
  assert.ok(dev.includes('export ANYSCRIBE_APP=1\nexport PIP_USER=1\nexport PYTHONUSERBASE="$HOME/.anyscribe/runtime"\n'));
  assert.ok(dev.endsWith(`exec '/x/it'\\''s python' -m anyscribe "$@"\n`));
  assert.ok(!dev.includes('ANYSCRIBE_ELECTRON'), 'dev: no Electron runtime');
  const packaged = terminal.commandScript({ appVersion: '0.20.0', python: '/A/Resources/python/bin/python3', packaged: true, resourcesPath: '/A/Resources', execPath: '/A/MacOS/anyscribe' });
  assert.ok(packaged.includes(`export PATH='/A/Resources/bin':"$PATH"\nexport ANYSCRIBE_ELECTRON='/A/MacOS/anyscribe'\n`));
});

test('the written command runs the app\'s Python with the engine environment', async () => {
  const h = home();
  const r = await terminal.turnOn(ctx(h));
  assert.equal(r.ok, true);
  const out = execFileSync(cmdPath(h), ['--version'], { env: { HOME: h, PATH: '/usr/bin:/bin' } }).toString();
  assert.equal(out.trim(), `anyscribe v0.20.0 app=1 pipuser=1 userbase=${h}/.anyscribe/runtime`);
  assert.equal(fs.statSync(cmdPath(h)).mode & 0o777, 0o755);
});

// ---- the login shell ----

test('login-shell output: only the text between our markers counts, whatever the rc files print', () => {
  const { markers } = terminal.shellScript('t0k3n');
  const out = [
    'Welcome back',
    'a line with no newline',
    markers.begin,
    '/Users/me/.local/bin/anyscribe',
    '',
    markers.path,
    '/Users/me/.local/bin:/usr/bin:/bin',
    markers.end,
    'logout noise',
  ].join('\n');
  assert.deepEqual(terminal.parseShellOutput(out, markers), { found: '/Users/me/.local/bin/anyscribe', pathDirs: ['/Users/me/.local/bin', '/usr/bin', '/bin'] });
  const none = `noise\n${markers.begin}\n\n${markers.path}\n/usr/bin\n${markers.end}\n`;
  assert.deepEqual(terminal.parseShellOutput(none, markers), { found: null, pathDirs: ['/usr/bin'] });
  assert.equal(terminal.parseShellOutput(`noise\n${markers.begin}\n/x\n`, markers), null, 'no end marker: unknown');
  // A forged marker from another run's token is not ours.
  const other = terminal.shellScript('another');
  assert.equal(terminal.parseShellOutput(none, other.markers), null);
});

test('the real zsh and bash, with noisy profiles: what Terminal runs and its PATH', async () => {
  for (const shell of [ZSH, BASH]) {
    const h = home({ shell, dirs: ['otherbin'] });
    fs.mkdirSync(path.join(h, 'otherbin'));
    let sh = await terminal.askLoginShell(ctx(h, { shell }));
    assert.equal(sh.ok, true, `${shell}: ${sh.reason}`);
    assert.equal(sh.found, null, `${shell}: no anyscribe yet`);
    assert.equal(sh.pathDirs[0], path.join(h, 'otherbin'), `${shell}: the profile's PATH`);
    fs.writeFileSync(path.join(h, 'otherbin', 'anyscribe'), '#!/bin/sh\n', { mode: 0o755 });
    sh = await terminal.askLoginShell(ctx(h, { shell }));
    assert.equal(sh.found, path.join(h, 'otherbin', 'anyscribe'), shell);
  }
});

test('a login shell that hangs or cannot run: PATH unknown, and the status says why', async () => {
  const h = home();
  const hang = path.join(ROOT, 'hanging-shell');
  fs.writeFileSync(hang, '#!/bin/sh\necho "starting"\nsleep 30\n', { mode: 0o755 });
  const t0 = Date.now();
  const sh = await terminal.askLoginShell(ctx(h, { shell: hang, shellTimeoutMs: 500 }));
  assert.ok(Date.now() - t0 < 3000, 'gave up at the timeout');
  assert.equal(sh.ok, false);
  assert.match(sh.reason, /couldn't ask your Terminal's shell \(hanging-shell\).*longer than 5 seconds/);
  const missing = await terminal.status(ctx(h, { shell: '/nonexistent/zsh' }));
  assert.equal(missing.state, 'off');
  assert.equal(missing.uses, null);
  assert.match(missing.reason, /couldn't ask your Terminal's shell \(zsh\)/);
});

// ---- the states ----

test('states: off, then path-missing, then on after addToPath', async () => {
  const h = home();
  let s = await terminal.status(ctx(h));
  assert.deepEqual(
    { state: s.state, command: s.command, uses: s.uses, claudeCode: s.claudeCode, skill: s.skill, ok: s.ok },
    { state: 'off', command: null, uses: null, claudeCode: false, skill: 'not-applicable', ok: true }
  );
  s = await terminal.turnOn(ctx(h));
  assert.equal(s.state, 'path-missing', 'written, but the login shell does not look in ~/.local/bin');
  assert.equal(s.command, cmdPath(h));
  const added = await terminal.addToPath(ctx(h));
  assert.deepEqual(added, { ok: true, file: path.join(h, '.zprofile'), line: 'export PATH="$HOME/.local/bin:$PATH"' });
  s = await terminal.status(ctx(h));
  assert.equal(s.state, 'on');
  assert.deepEqual(s.uses, { path: cmdPath(h), version: '0.20.0', via: 'app' });
  assert.equal(s.appVersion, '0.20.0');
});

test('state other-copy: Terminal runs a copy installed with uv, named with its version', async () => {
  const h = home({ dirs: ['.local/bin'] });
  uvCopy(h);
  const s = await terminal.status(ctx(h));
  assert.equal(s.state, 'other-copy');
  assert.deepEqual(s.uses, { path: cmdPath(h), version: '0.19.0', via: 'uv' });
  assert.deepEqual(s.occupant, { path: cmdPath(h), via: 'uv', version: '0.19.0' }, 'Switch can replace it');
  assert.equal(s.command, null);
});

test('ours is written but another anyscribe comes first on PATH: other-copy', async () => {
  const h = home({ dirs: ['first', '.local/bin'] });
  fs.mkdirSync(path.join(h, 'first'));
  fs.writeFileSync(path.join(h, 'first', 'anyscribe'), '#!/usr/bin/env python3\n', { mode: 0o755 });
  const s = await terminal.turnOn(ctx(h));
  assert.equal(s.state, 'other-copy');
  assert.equal(s.command, cmdPath(h));
  assert.equal(s.uses.via, 'pip');
  assert.equal(s.reason, `Terminal finds another anyscribe at ${path.join(h, 'first', 'anyscribe')} first.`, 'F1: says which copy wins');
  assert.equal(s.occupant, null, 'F1: nothing to switch: ~/.local/bin/anyscribe is already ours');
});

test('F1: a uv copy at ~/.local/bin while Terminal does not look there: off, and the occupant is named', async () => {
  const h = home();
  uvCopy(h);
  const s = await terminal.status(ctx(h));
  assert.equal(s.state, 'off');
  assert.equal(s.uses, null);
  assert.deepEqual(s.occupant, { path: cmdPath(h), via: 'uv', version: '0.19.0' });
});

test('the login shell cannot be asked: ours counts as on, and the reason says PATH is unknown', async () => {
  const h = home();
  await terminal.turnOn(ctx(h));
  const s = await terminal.status(ctx(h, { shell: '/nonexistent/zsh' }));
  assert.equal(s.state, 'on');
  assert.equal(s.uses, null);
  assert.match(s.reason, /couldn't ask/);
});

// ---- ownership ----

test('ownership is the marker and the recorded hash: an edited copy or an unrecorded one is not ours', async () => {
  const h = home();
  await terminal.turnOn(ctx(h));
  const f = terminal.files(h);
  assert.equal(terminal.isOurs(f, terminal.readRecord(f)), true);
  fs.appendFileSync(cmdPath(h), '# edited\n');
  assert.equal(terminal.isOurs(f, terminal.readRecord(f)), false, 'edited: hash differs');
  const h2 = home();
  fs.mkdirSync(path.dirname(cmdPath(h2)), { recursive: true });
  fs.copyFileSync(cmdPath(h), cmdPath(h2));
  assert.equal(terminal.isOurs(terminal.files(h2), terminal.readRecord(terminal.files(h2))), false, 'never recorded here');
});

test('guard: turnOn never overwrites a file that is not ours without replace', async () => {
  for (const make of [uvCopy, pipCopy]) {
    const h = home({ dirs: ['.local/bin'] });
    make(h);
    const before = fs.lstatSync(cmdPath(h)).isSymbolicLink() ? fs.readlinkSync(cmdPath(h)) : read(cmdPath(h));
    const r = await terminal.turnOn(ctx(h), { replace: false });
    assert.equal(r.ok, false, 'refused');
    assert.match(r.reason, /Another anyscribe is already at ~\/\.local\/bin\/anyscribe/);
    assert.equal(r.state, 'other-copy');
    const after = fs.lstatSync(cmdPath(h)).isSymbolicLink() ? fs.readlinkSync(cmdPath(h)) : read(cmdPath(h));
    assert.equal(after, before, 'the other file is untouched');
    assert.equal(fs.existsSync(backupPath(h)), false, 'nothing moved');
  }
});

test('replace backs up a symlink, and turnOff puts back exactly that symlink', async () => {
  const h = home({ dirs: ['.local/bin'] });
  const target = uvCopy(h);
  const on = await terminal.turnOn(ctx(h), { replace: true });
  assert.equal(on.ok, true);
  assert.equal(on.state, 'on');
  assert.equal(fs.readlinkSync(backupPath(h)), target, 'the symlink itself was moved, not its target');
  assert.deepEqual(record(h).replaced, { kind: 'symlink', target });
  const off = await terminal.turnOff(ctx(h));
  assert.equal(off.ok, true);
  assert.equal(fs.lstatSync(cmdPath(h)).isSymbolicLink(), true);
  assert.equal(fs.readlinkSync(cmdPath(h)), target);
  assert.equal(fs.existsSync(backupPath(h)), false);
  assert.equal(off.state, 'other-copy', 'Terminal runs the uv copy again');
  assert.deepEqual(record(h), {});
});

test('replace backs up a regular file, and turnOff puts back its exact content and mode', async () => {
  const h = home({ dirs: ['.local/bin'] });
  pipCopy(h);
  const content = read(cmdPath(h));
  await terminal.turnOn(ctx(h), { replace: true });
  assert.equal(read(backupPath(h)), content);
  assert.equal(record(h).replaced.kind, 'file');
  const off = await terminal.turnOff(ctx(h));
  assert.equal(off.ok, true);
  assert.equal(read(cmdPath(h)), content);
  assert.equal(fs.statSync(cmdPath(h)).mode & 0o777, 0o750);
});

test('turning on again keeps what it replaced; an older backup is never deleted', async () => {
  const h = home({ dirs: ['.local/bin'] });
  const target = uvCopy(h);
  await terminal.turnOn(ctx(h), { replace: true });
  await terminal.turnOn(ctx(h));
  assert.deepEqual(record(h).replaced, { kind: 'symlink', target }, 'refreshing ours keeps the record');
  // uv rewrote the command since: switching again keeps both copies.
  fs.unlinkSync(cmdPath(h));
  fs.symlinkSync(`${target}-new`, cmdPath(h));
  await terminal.turnOn(ctx(h), { replace: true });
  const kept = fs.readdirSync(path.dirname(backupPath(h)));
  assert.equal(kept.length, 2, `both kept: ${kept}`);
  assert.equal(fs.readlinkSync(backupPath(h)), `${target}-new`);
});

test('guard: a refresh that cannot be written keeps ours ours, and turnOff still restores the original (C4)', async () => {
  const h = home({ dirs: ['.local/bin'] });
  const target = uvCopy(h);
  await terminal.turnOn(ctx(h), { replace: true });
  const before = read(cmdPath(h));
  const recorded = record(h).sha256;
  const bin = path.dirname(cmdPath(h));
  fs.chmodSync(bin, 0o555); // the new command cannot be written
  let r;
  try {
    r = await terminal.turnOn(ctx(h, { python: '/a/moved/python3', appVersion: '0.20.1' }));
  } finally {
    fs.chmodSync(bin, 0o755);
  }
  assert.equal(r.ok, false);
  assert.match(r.reason, /Couldn't write ~\/\.local\/bin\/anyscribe: EACCES/);
  assert.equal(read(cmdPath(h)), before, 'the command is untouched');
  assert.equal(record(h).sha256, recorded, 'and still recorded as ours');
  const off = await terminal.turnOff(ctx(h));
  assert.equal(off.ok, true, JSON.stringify(off));
  assert.equal(fs.readlinkSync(cmdPath(h)), target, 'the uv copy is back');
});

test('guard: temp files are created exclusively; a planted symlink and the profile it points at are left as they were (A3)', async () => {
  const h = home({ dirs: ['.local/bin'] });
  const profile = path.join(h, '.zprofile');
  const profileBytes = read(profile);
  const runtime = path.join(h, '.anyscribe', 'runtime');
  fs.mkdirSync(runtime, { recursive: true });
  fs.mkdirSync(path.dirname(cmdPath(h)), { recursive: true });
  const recordTemp = path.join(runtime, '.terminal.json.planted.tmp');
  const commandTemp = path.join(path.dirname(cmdPath(h)), '.anyscribe.planted.tmp');
  const tag = terminal.naming.tempTag;
  terminal.naming.tempTag = () => 'planted';
  try {
    // The record's temp name is taken: nothing written through it; the command's own temp is cleaned up.
    fs.symlinkSync(profile, recordTemp);
    let r = await terminal.turnOn(ctx(h));
    assert.equal(r.ok, false);
    assert.match(r.reason, /EEXIST/);
    assert.equal(read(profile), profileBytes, 'the profile is unchanged');
    assert.equal(fs.readlinkSync(recordTemp), profile, 'the planted link is still there');
    assert.deepEqual(fs.readdirSync(path.dirname(cmdPath(h))), [], 'no command and no temp of ours left');
    // The command's temp name is taken too.
    fs.symlinkSync(profile, commandTemp);
    r = await terminal.turnOn(ctx(h));
    assert.equal(r.ok, false);
    assert.equal(read(profile), profileBytes, 'the profile is unchanged');
    assert.equal(fs.readlinkSync(commandTemp), profile);
    assert.equal(fs.readlinkSync(recordTemp), profile);
  } finally {
    terminal.naming.tempTag = tag;
  }
});

test('guard: a record that cannot be saved leaves the command untouched and ours (A4)', async () => {
  const h = home({ dirs: ['.local/bin'] });
  const target = uvCopy(h);
  await terminal.turnOn(ctx(h), { replace: true });
  const before = read(cmdPath(h));
  const runtime = path.join(h, '.anyscribe', 'runtime');
  fs.chmodSync(runtime, 0o555); // unwritable from the start of the refresh
  let r;
  try {
    r = await terminal.turnOn(ctx(h, { python: '/a/moved/python3', appVersion: '0.20.1' }));
  } finally {
    fs.chmodSync(runtime, 0o755);
  }
  assert.equal(r.ok, false);
  assert.match(r.reason, /EACCES/);
  assert.equal(read(cmdPath(h)), before, "the command's bytes are identical");
  const f = terminal.files(h);
  assert.equal(terminal.isOurs(f, terminal.readRecord(f)), true, 'still ours');
  const off = await terminal.turnOff(ctx(h));
  assert.equal(off.ok, true, JSON.stringify(off));
  assert.equal(fs.readlinkSync(cmdPath(h)), target, 'the uv copy is back');
});

test('guard: in the crash window the record names the new hash and still accepts the old one (round 3)', async () => {
  const h = home({ dirs: ['.local/bin'] });
  const target = uvCopy(h);
  await terminal.turnOn(ctx(h), { replace: true });
  const f = terminal.files(h);
  const rec = terminal.readRecord(f);
  // As if a refresh had committed its record and stopped before moving the new command in.
  fs.writeFileSync(f.record, JSON.stringify({ ...rec, sha256: 'f'.repeat(64), previousSha256: rec.sha256 }));
  assert.equal(terminal.isOurs(f, terminal.readRecord(f)), true, 'the old command is still ours');
  const off = await terminal.turnOff(ctx(h));
  assert.equal(off.ok, true);
  assert.equal(fs.readlinkSync(cmdPath(h)), target);
});

test('guard: turnOff refuses when ours was changed and something can be put back; then each choice', async () => {
  for (const choice of ['restore', 'keep-current']) {
    const h = home({ dirs: ['.local/bin'] });
    const target = uvCopy(h);
    await terminal.turnOn(ctx(h), { replace: true });
    fs.appendFileSync(cmdPath(h), '# edited by hand\n');
    const edited = read(cmdPath(h));
    const r = await terminal.turnOff(ctx(h));
    assert.equal(r.ok, false);
    assert.equal(r.needsChoice, 'keep-current-or-restore');
    assert.match(r.reason, /has changed since anyscribe put it there/);
    assert.equal(read(cmdPath(h)), edited, 'nothing touched');
    assert.equal(fs.readlinkSync(backupPath(h)), target, 'the backup is still there');
    const answered = await terminal.turnOff(ctx(h), { choice });
    assert.equal(answered.ok, true, choice);
    if (choice === 'restore') {
      assert.equal(fs.readlinkSync(cmdPath(h)), target, 'restore: the uv copy is back');
      const aside = fs.readdirSync(path.dirname(backupPath(h)));
      assert.equal(aside.length, 1);
      assert.equal(read(path.join(path.dirname(backupPath(h)), aside[0])), edited, 'the edited file is kept, not deleted');
    } else {
      assert.equal(read(cmdPath(h)), edited, 'keep-current: the edited file stays');
      assert.equal(fs.readlinkSync(backupPath(h)), target, 'and the backup is kept');
    }
    assert.deepEqual(record(h), {});
  }
});

test('guard: turnOff leaves a changed command alone when there is nothing to put back', async () => {
  const h = home();
  await terminal.turnOn(ctx(h));
  fs.appendFileSync(cmdPath(h), '# edited by hand\n');
  const edited = read(cmdPath(h));
  const r = await terminal.turnOff(ctx(h));
  assert.equal(r.ok, true);
  assert.match(r.reason, /was changed since anyscribe wrote it, so it was left as it is/);
  assert.equal(read(cmdPath(h)), edited, 'not removed');
  assert.deepEqual(record(h), {});
});

test('turnOff after ours was deleted: asks before putting the old one back', async () => {
  const h = home({ dirs: ['.local/bin'] });
  uvCopy(h);
  await terminal.turnOn(ctx(h), { replace: true });
  fs.unlinkSync(cmdPath(h));
  const r = await terminal.turnOff(ctx(h));
  assert.equal(r.needsChoice, 'keep-current-or-restore');
  assert.match(r.reason, /was removed since/);
  assert.equal(fs.existsSync(cmdPath(h)), false);
});

test('turnOff when it was never on changes nothing', async () => {
  const h = home({ dirs: ['.local/bin'] });
  pipCopy(h);
  const r = await terminal.turnOff(ctx(h));
  assert.equal(r.ok, true);
  assert.equal(r.state, 'other-copy');
  assert.equal(read(cmdPath(h)), '#!/usr/bin/python3\n# pip console script\nimport sys\n');
});

// ---- the skill ----

test('the skill: installed with Claude Code, never without it (no surprise skill)', async () => {
  const before = calls();
  const without = home();
  const r = await terminal.turnOn(ctx(without));
  assert.equal(r.skill, 'not-applicable');
  assert.ok(!calls().slice(before.length).includes('install-skill'), 'no skill install without ~/.claude');
  const h = home({ claude: true });
  const on = await terminal.turnOn(ctx(h));
  assert.equal(on.skill, 'installed');
  assert.match(calls(), /-m anyscribe install-skill --force/);
});

test('the skill could not be installed: Terminal is on, the skill is missing and says why; Try again', async () => {
  const h = home({ claude: true, dirs: ['.local/bin'] });
  fs.writeFileSync(path.join(h, 'skill-fails'), '');
  const on = await terminal.turnOn(ctx(h));
  assert.equal(on.ok, true, 'the command was written');
  assert.equal(on.state, 'on');
  assert.equal(on.skill, 'missing');
  assert.equal(on.reason, "Couldn't write to ~/.claude/skills (permission denied).");
  assert.equal((await terminal.status(ctx(h))).reason, "Couldn't write to ~/.claude/skills (permission denied).", 'the status keeps saying why');
  const again = await terminal.retrySkill(ctx(h));
  assert.equal(again.ok, false);
  fs.unlinkSync(path.join(h, 'skill-fails'));
  const fixed = await terminal.retrySkill(ctx(h));
  assert.equal(fixed.ok, true);
  assert.equal(fixed.skill, 'installed');
  assert.equal(fixed.reason, null);
});

test('guard: a failed update over an older skill reads missing, with the reason, until an install succeeds (C3)', async () => {
  const h = home({ claude: true, dirs: ['.local/bin'] });
  const skillFile = path.join(h, '.claude', 'skills', 'anyscribe', 'SKILL.md');
  fs.mkdirSync(path.dirname(skillFile), { recursive: true });
  fs.writeFileSync(skillFile, 'an older skill\n');
  const old = new Date(Date.now() - 3600_000);
  fs.utimesSync(skillFile, old, old);
  fs.writeFileSync(path.join(h, 'skill-fails'), '');
  const on = await terminal.turnOn(ctx(h));
  assert.equal(on.skill, 'missing', 'the older SKILL.md does not make it installed');
  assert.equal(on.reason, "Couldn't write to ~/.claude/skills (permission denied).");
  assert.equal((await terminal.status(ctx(h))).skill, 'missing');
  // Exit 0 without writing it: still not installed.
  fs.renameSync(path.join(h, 'skill-fails'), path.join(h, 'skill-noop'));
  const noop = await terminal.retrySkill(ctx(h));
  assert.equal(noop.skill, 'missing');
  assert.match(noop.reason, /finished without writing it/);
  fs.rmSync(path.join(h, 'skill-noop'));
  const fixed = await terminal.retrySkill(ctx(h));
  assert.deepEqual([fixed.ok, fixed.skill, fixed.reason], [true, 'installed', null]);
});

test('guard: turnOff removes the skill only when Terminal is left with no anyscribe', async () => {
  // Another copy elsewhere on PATH: the skill stays.
  const shared = home({ claude: true, dirs: ['otherbin', '.local/bin'] });
  fs.mkdirSync(path.join(shared, 'otherbin'));
  fs.writeFileSync(path.join(shared, 'otherbin', 'anyscribe'), '#!/bin/sh\necho "anyscribe v0.18.0"\n', { mode: 0o755 });
  await terminal.turnOn(ctx(shared));
  let off = await terminal.turnOff(ctx(shared));
  assert.equal(off.ok, true);
  assert.equal(fs.existsSync(path.join(shared, '.claude', 'skills', 'anyscribe', 'SKILL.md')), true, 'kept: another anyscribe is left');
  assert.equal(off.state, 'other-copy');
  // A replaced copy put back: the skill stays.
  const restored = home({ claude: true, dirs: ['.local/bin'] });
  uvCopy(restored);
  await terminal.turnOn(ctx(restored), { replace: true });
  await terminal.turnOff(ctx(restored));
  assert.equal(fs.existsSync(path.join(restored, '.claude', 'skills', 'anyscribe')), true, 'kept: the uv copy is back');
  // The login shell cannot be asked: kept, and it says so.
  const unknown = home({ claude: true, dirs: ['.local/bin'] });
  await terminal.turnOn(ctx(unknown));
  off = await terminal.turnOff(ctx(unknown, { shell: '/nonexistent/zsh' }));
  assert.equal(fs.existsSync(path.join(unknown, '.claude', 'skills', 'anyscribe')), true, 'kept: unknown is not none');
  assert.match(off.reason, /skill was kept/);
  // Nothing left: removed.
  const alone = home({ claude: true, dirs: ['.local/bin'] });
  await terminal.turnOn(ctx(alone));
  off = await terminal.turnOff(ctx(alone));
  assert.equal(fs.existsSync(path.join(alone, '.claude', 'skills', 'anyscribe')), false, 'removed: no anyscribe left');
  assert.equal(fs.existsSync(path.join(alone, '.claude')), true, 'only the skill folder');
  assert.equal(off.state, 'off');
  assert.equal(off.skill, 'missing');
});

// ---- addToPath ----

test('guard: addToPath writes one line to the login shell\'s own file, never twice', async () => {
  const h = home();
  fs.writeFileSync(path.join(h, '.zprofile'), 'export EDITOR=vim'); // no newline at the end
  const line = 'export PATH="$HOME/.local/bin:$PATH"';
  assert.equal((await terminal.addToPath(ctx(h))).ok, true);
  assert.equal((await terminal.addToPath(ctx(h))).ok, true);
  assert.equal(read(path.join(h, '.zprofile')), `export EDITOR=vim\n${line}\n`, 'once, on its own line');
  assert.equal(fs.existsSync(path.join(h, '.bash_profile')), false, 'never another shell\'s file');
  const b = home({ shell: BASH });
  fs.rmSync(path.join(b, '.bash_profile'));
  const r = await terminal.addToPath(ctx(b, { shell: BASH }));
  assert.deepEqual(r, { ok: true, file: path.join(b, '.bash_profile'), line });
  assert.equal(read(path.join(b, '.bash_profile')), `${line}\n`, 'created when missing');
  assert.equal(fs.existsSync(path.join(b, '.zprofile')), false);
});

test('addToPath: bash reading ~/.profile, and other shells, are left to the person', async () => {
  const b = home({ shell: BASH });
  fs.rmSync(path.join(b, '.bash_profile'));
  fs.writeFileSync(path.join(b, '.profile'), 'export X=1\n');
  const r = await terminal.addToPath(ctx(b, { shell: BASH }));
  assert.equal(r.ok, false);
  assert.match(r.reason, /Your bash reads ~\/\.profile; add this line to it by hand/);
  assert.equal(fs.existsSync(path.join(b, '.bash_profile')), false, 'not created: it would hide ~/.profile');
  const f = home();
  const fish = await terminal.addToPath(ctx(f, { shell: '/opt/homebrew/bin/fish' }));
  assert.equal(fish.ok, false);
  assert.match(fish.reason, /Add ~\/\.local\/bin to your shell's PATH by hand/);
  assert.deepEqual(fs.readdirSync(f).sort(), ['.zprofile', '.zshrc'], 'nothing written');
});

test('guard: addToPath says when the line has no effect because a later rc file resets PATH (F6)', async () => {
  const h = home();
  fs.appendFileSync(path.join(h, '.zshrc'), 'export PATH=/usr/bin:/bin\n');
  const r = await terminal.addToPath(ctx(h));
  assert.equal(r.ok, true);
  assert.equal(r.reason, 'The line is in ~/.zprofile, but your shell setup removes it again later (check ~/.zshrc).');
  assert.equal(read(path.join(h, '.zprofile')).split('\n').filter((l) => l === terminal.PATH_LINE).length, 1, 'the line is there once');
});

test('terminalState: every state the screens show', () => {
  const s = terminal.terminalState;
  assert.equal(s({ ours: false, shellKnown: true }), 'off');
  assert.equal(s({ ours: false, shellKnown: true, foundOther: true }), 'other-copy');
  assert.equal(s({ ours: true, shellKnown: true, foundOurs: true }), 'on');
  assert.equal(s({ ours: true, shellKnown: true }), 'path-missing');
  assert.equal(s({ ours: true, shellKnown: true, foundOther: true }), 'other-copy');
  assert.equal(s({ ours: true, shellKnown: false }), 'on');
});
