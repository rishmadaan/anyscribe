// The old browser launcher (src/old-launcher.js) against a throwaway HOME: never the real
// ~/Applications, ~/Library or ~/.anyscribe. `desktop uninstall` is a stand-in that removes
// what each test tells it to; the menu bar icon is a real process with a tray's command line.
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const launcher = require('../src/old-launcher');

const ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'anyscribe-launcher-test-'));
const started = [];
test.after(() => {
  for (const c of started) if (c.exitCode === null && c.signalCode === null) c.kill('SIGKILL');
  fs.rmSync(ROOT, { recursive: true, force: true });
});

let n = 0;
// A home with all three pieces: the launcher, the login item, and a running tray named in tray.pid.
async function installed({ tray = true } = {}) {
  const home = path.join(ROOT, `home-${n++}`);
  const f = launcher.files(home);
  fs.mkdirSync(path.join(f.launcher, 'Contents'), { recursive: true });
  fs.mkdirSync(path.dirname(f.loginItem), { recursive: true });
  fs.writeFileSync(f.loginItem, '<plist/>');
  fs.mkdirSync(path.dirname(f.pidFile), { recursive: true });
  let child = null;
  if (tray) {
    child = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1 << 30)', '--', '-m', 'anyscribe', 'tray'], { stdio: 'ignore' });
    started.push(child);
    await new Promise((r) => child.once('spawn', r));
    fs.writeFileSync(f.pidFile, `${child.pid}\n`);
  }
  return { home, f, child };
}

// A stand-in for `python -m anyscribe desktop uninstall --json` that removes only `which`.
function uninstaller({ f, child }, which, calls = []) {
  return async (cmd, args, opts) => {
    calls.push([cmd, args, opts.env]);
    if (which.includes('launcher')) fs.rmSync(f.launcher, { recursive: true, force: true });
    if (which.includes('loginItem')) fs.rmSync(f.loginItem, { force: true });
    if (which.includes('menuBarIcon') && child) {
      child.kill('SIGTERM');
      await new Promise((r) => child.once('exit', r));
    }
    return { out: '{"stopped": true}', err: '', code: 0 };
  };
}

function ctx(setup, extra = {}) {
  const turnedOn = [];
  return {
    turnedOn,
    ctx: {
      home: setup.home,
      platform: 'darwin',
      python: '/app/python3',
      env: { HOME: setup.home },
      setStartAtLogin: (on) => turnedOn.push(on),
      loginItemState: () => (turnedOn.includes(true) ? 'enabled' : 'not-registered'),
      ...extra,
    },
  };
}

test('status: each piece checked; installed only on a Mac', async () => {
  const s = await installed();
  assert.deepEqual(await launcher.status({ home: s.home, platform: 'darwin' }), {
    ok: true,
    installed: true,
    pieces: { launcher: 'present', loginItem: 'present', menuBarIcon: 'running' },
  });
  const linux = await launcher.status({ home: s.home, platform: 'linux' });
  assert.equal(linux.installed, false, 'elsewhere installed is false');
  assert.equal(linux.pieces.menuBarIcon, 'running', 'status still reports the pieces');
  const empty = path.join(ROOT, 'empty-home');
  assert.deepEqual(await launcher.status({ home: empty, platform: 'darwin' }), {
    ok: true,
    installed: false,
    pieces: { launcher: 'absent', loginItem: 'absent', menuBarIcon: 'not running' },
  });
});

test('guard: the menu bar icon is running only when tray.pid names a live anyscribe tray', async () => {
  const s = await installed({ tray: false });
  fs.writeFileSync(s.f.pidFile, `${process.pid}\n`); // alive, but this test runner, not a tray
  assert.equal(await launcher.trayRunning(s.home), false, 'a reused pid is not a tray');
  const gone = spawn(process.execPath, ['-e', '0', '--', '-m', 'anyscribe', 'tray']);
  await new Promise((r) => gone.once('exit', r));
  fs.writeFileSync(s.f.pidFile, `${gone.pid}\n`);
  assert.equal(await launcher.trayRunning(s.home), false, 'a dead pid');
  fs.writeFileSync(s.f.pidFile, 'garbage');
  assert.equal(await launcher.trayRunning(s.home), false, 'an unreadable pid');
  assert.equal(launcher.TRAY_COMMAND.test('/Users/me/.local/bin/anyscribe tray'), true);
  assert.equal(launcher.TRAY_COMMAND.test('/usr/bin/python3 -m anyscribe tray --port 8470'), true);
  assert.equal(launcher.TRAY_COMMAND.test('/usr/bin/python3 -m anyscribe ui --port 8470'), false);
  assert.equal(launcher.TRAY_COMMAND.test('/Users/me/anyscribe-notes/tray'), false);
});

test('remove: runs desktop uninstall with the engine environment, all gone, Start at login carried over', async () => {
  const s = await installed();
  const calls = [];
  const { ctx: c, turnedOn } = ctx(s, { run: uninstaller(s, ['launcher', 'loginItem', 'menuBarIcon'], calls) });
  const r = await launcher.remove(c);
  assert.deepEqual(r, {
    ok: true,
    pieces: { launcher: 'removed', loginItem: 'removed', menuBarIcon: 'stopped' },
    startAtLoginCarriedOver: true,
  });
  assert.deepEqual(calls, [['/app/python3', ['-m', 'anyscribe', 'desktop', 'uninstall', '--json'], { HOME: s.home }]]);
  assert.deepEqual(turnedOn, [true]);
});

for (const left of ['launcher', 'loginItem', 'menuBarIcon']) {
  test(`guard: remove checks the ${left} itself; ok only when all three are gone`, async () => {
    const s = await installed();
    const removed = ['launcher', 'loginItem', 'menuBarIcon'].filter((p) => p !== left);
    const { ctx: c } = ctx(s, { run: uninstaller(s, removed) });
    const r = await launcher.remove(c);
    assert.equal(r.ok, false);
    const expected = { launcher: 'removed', loginItem: 'removed', menuBarIcon: 'stopped' };
    expected[left] = left === 'menuBarIcon' ? 'still running' : 'still there';
    assert.deepEqual(r.pieces, expected);
    assert.match(r.reason, /^Cleanup didn't finish: /);
  });
}

test('Start at login is carried over only when the old login item was there and is now gone', async () => {
  const kept = await installed({ tray: false });
  const one = ctx(kept, { run: uninstaller(kept, ['launcher']) });
  assert.equal((await launcher.remove(one.ctx)).startAtLoginCarriedOver, false);
  assert.deepEqual(one.turnedOn, [], 'its login item is still there: not turned on');
  const none = await installed({ tray: false });
  fs.rmSync(none.f.loginItem);
  const two = ctx(none, { run: uninstaller(none, ['launcher']) });
  const r = await launcher.remove(two.ctx);
  assert.equal(r.ok, true);
  assert.equal(r.startAtLoginCarriedOver, false);
  assert.deepEqual(two.turnedOn, [], 'there was no login item: not turned on');
});

test('remove: a failed uninstall is reported with each piece; only a Mac removes', async () => {
  const s = await installed({ tray: false });
  const { ctx: c } = ctx(s, { run: async () => ({ out: '', err: 'Traceback\nOSError: launchctl failed\n', code: 1 }) });
  const r = await launcher.remove(c);
  assert.equal(r.ok, false);
  assert.match(r.reason, /the launcher is still in ~\/Applications, its login item is still there\. The uninstall said: OSError: launchctl failed\./);
  let ran = false;
  const linux = await launcher.remove({ ...c, platform: 'linux', run: async () => ((ran = true), { code: 0 }) });
  assert.equal(linux.ok, false);
  assert.equal(ran, false, 'nothing run off a Mac');
});

// The engine's own rule for the port `desktop uninstall` stops (core/desktop.py at b22df16).
function writePlist(f, port) {
  fs.mkdirSync(path.dirname(f.loginItem), { recursive: true });
  fs.writeFileSync(
    f.loginItem,
    `<?xml version="1.0"?>\n<plist version="1.0"><dict><key>Label</key><string>com.anyscribe.tray</string><key>ProgramArguments</key><array><string>/py</string><string>-m</string><string>anyscribe</string><string>tray</string><string>--port</string><string>${port}</string></array></dict></plist>`
  );
}

test('uninstall target: the manifest port, else the login item port, else 8457', async () => {
  const s = await installed({ tray: false });
  writePlist(s.f, 8470);
  assert.equal(launcher.uninstallTarget(s.home), 8470, 'no manifest: the login item');
  fs.writeFileSync(path.join(s.home, '.anyscribe', 'desktop.json'), JSON.stringify({ port: 8471 }));
  assert.equal(launcher.uninstallTarget(s.home), 8471, 'the manifest wins');
  assert.deepEqual((await launcher.recordedPorts(s.home)).sort(), [8457, 8470, 8471]);
  fs.writeFileSync(path.join(s.home, '.anyscribe', 'desktop.json'), '{}');
  assert.equal(launcher.uninstallTarget(s.home), 8470, 'an empty manifest counts as none, as in Python');
  fs.rmSync(s.f.loginItem);
  assert.equal(launcher.uninstallTarget(s.home), 8457);
});

test('guard: Start at login counts as carried over only when the system reads it back enabled (C5)', async () => {
  const s = await installed();
  const { ctx: c, turnedOn } = ctx(s, { run: uninstaller(s, ['launcher', 'loginItem', 'menuBarIcon']), loginItemState: () => 'requires-approval' });
  const r = await launcher.remove(c);
  assert.deepEqual(turnedOn, [true], 'it was asked for');
  assert.equal(r.ok, true, 'the old launcher is gone');
  assert.equal(r.startAtLoginCarriedOver, false);
  assert.equal(r.reason, 'This app is set to start at login, but macOS needs your approval: System Settings, General, Login Items.');
});

test('guard: a live old tray alone still counts as installed on a Mac (C6)', async () => {
  const s = await installed();
  fs.rmSync(s.f.launcher, { recursive: true });
  fs.rmSync(s.f.loginItem);
  assert.deepEqual(await launcher.status({ home: s.home, platform: 'darwin' }), {
    ok: true,
    installed: true,
    pieces: { launcher: 'absent', loginItem: 'absent', menuBarIcon: 'running' },
  });
});

// ---- round 5: the exact plist read and the live tray's own port ----

const logic = require('../src/logic');

function withPlutil(fake, fn) {
  const real = launcher.readers.plutil;
  launcher.readers.plutil = fake;
  return Promise.resolve(fn()).finally(() => (launcher.readers.plutil = real));
}

test('guard: a binary plist is read exactly through plutil: 8470, so the app picks 8471 (round 5)', async () => {
  const s = await installed({ tray: false });
  fs.writeFileSync(s.f.loginItem, Buffer.from('bplist00 not xml at all'));
  const seen = [];
  await withPlutil(
    (file) => (seen.push(file), JSON.stringify(['/py', '-m', 'anyscribe', 'tray', '--port', '8470'])),
    async () => {
      assert.equal(launcher.loginItemPort(s.home), 8470);
      assert.equal(launcher.uninstallTarget(s.home), 8470);
      assert.equal(logic.choosePort({ avoid: await launcher.recordedPorts(s.home) }), 8471);
    }
  );
  assert.equal(seen[0], s.f.loginItem, 'plutil was asked about the login item');
});

test('plutil failing: the XML read, then unknown (round 5)', async () => {
  const s = await installed({ tray: false });
  await withPlutil(
    () => {
      throw new Error('plutil: no such file');
    },
    async () => {
      writePlist(s.f, 8470);
      assert.equal(launcher.loginItemPort(s.home), 8470, 'the XML read');
      fs.writeFileSync(s.f.loginItem, Buffer.from('bplist00 not xml at all'));
      assert.equal(launcher.loginItemPort(s.home), null, 'unknown');
      assert.equal(logic.choosePort({ avoid: await launcher.recordedPorts(s.home) }), 8470);
    }
  );
});

for (const args of [['--port', '8470'], ['-p', '8470'], ['--port=8470'], ['-p8470']]) {
  test(`guard: no files, a live old tray started with ${args.join(' ')}: the app picks 8471 (round 5)`, async () => {
    const s = await installed({ tray: false });
    fs.rmSync(s.f.launcher, { recursive: true });
    fs.rmSync(s.f.loginItem);
    const tray = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1 << 30)', '--', '-m', 'anyscribe', 'tray', ...args], { stdio: 'ignore' });
    started.push(tray);
    await new Promise((r) => tray.once('spawn', r));
    fs.writeFileSync(s.f.pidFile, String(tray.pid));
    assert.deepEqual(await launcher.trayPort(s.home), { ports: [8470], readable: true });
    assert.equal(logic.choosePort({ avoid: await launcher.recordedPorts(s.home) }), 8471);
    tray.kill('SIGKILL');
  });
}

test("a live tray whose port can't be read: 8457 avoided, a note, and the start goes ahead (round 5)", async () => {
  const s = await installed({ tray: false });
  const tray = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1 << 30)', '--', '-m', 'anyscribe', 'tray', '--port', 'abc'], { stdio: 'ignore' });
  started.push(tray);
  await new Promise((r) => tray.once('spawn', r));
  fs.writeFileSync(s.f.pidFile, String(tray.pid));
  const notes = [];
  const ports = await launcher.recordedPorts(s.home, { note: (m) => notes.push(m) });
  assert.ok(ports.includes(8457));
  assert.equal(logic.choosePort({ avoid: ports }), 8470);
  assert.match(notes[0], /couldn't be read/);
  tray.kill('SIGKILL');
});

// E1: every port the command line names, so a saved port among them is not reused either.
async function trayWith(args) {
  const s = await installed({ tray: false });
  fs.rmSync(s.f.launcher, { recursive: true });
  fs.rmSync(s.f.loginItem);
  const tray = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1 << 30)', '--', '-m', 'anyscribe', 'tray', ...args], { stdio: 'ignore' });
  started.push(tray);
  await new Promise((r) => tray.once('spawn', r));
  fs.writeFileSync(s.f.pidFile, String(tray.pid));
  return { s, tray };
}

test('guard: a repeated --port avoids every port named, and a saved one among them is not reused (E1)', async () => {
  const { s, tray } = await trayWith(['--port', '8457', '--port', '8470']);
  const avoid = await launcher.recordedPorts(s.home);
  assert.ok(avoid.includes(8457) && avoid.includes(8470), `avoid: ${avoid}`);
  assert.equal(logic.choosePort({ avoid }), 8471, 'neither port');
  assert.equal(logic.choosePort({ saved: 8470, avoid }), 8471, 'the saved 8470 is not reused');
  tray.kill('SIGKILL');
});

test('guard: the attached short form -p8470 avoids 8470, saved or not (E1)', async () => {
  const { s, tray } = await trayWith(['-p8470']);
  const avoid = await launcher.recordedPorts(s.home);
  assert.equal(logic.choosePort({ avoid }), 8471);
  assert.equal(logic.choosePort({ saved: 8470, avoid }), 8471, 'the saved 8470 is not reused');
  tray.kill('SIGKILL');
});
