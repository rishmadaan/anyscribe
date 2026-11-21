// Removing the old launcher against the real engine and the real `desktop uninstall` (round 3,
// A1 and A2): the app's engine is never the uninstall's target, because the uninstall runs while
// the engine is down. Needs a Python with anyscribe (slice 2a) installed:
//   ANYSCRIBE_DEV_PYTHON=/path/to/python node --test test/removal.e2e.js
// Not part of `npm test`. Throwaway homes under the system temp folder; port 8470 must be free.
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn, execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const logic = require('../src/logic');
const { Engine, AppLog, health } = require('../src/engine');
const launcher = require('../src/old-launcher');
const { runCapture, killHelpers } = require('../src/run');

const python = process.env.ANYSCRIBE_DEV_PYTHON;
const ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'anyscribe-removal-e2e-'));
const started = [];
const engines = [];
test.afterEach(async () => {
  for (const e of engines.splice(0)) await e.stop(); // each test needs 8470 free
});
test.after(async () => {
  for (const c of started) if (c.exitCode === null && c.signalCode === null) c.kill('SIGKILL');
  fs.rmSync(ROOT, { recursive: true, force: true });
});

const alive = (pid) => {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
};

let n = 0;
async function realEngine() {
  const home = path.join(ROOT, `home-${n++}`);
  fs.mkdirSync(path.join(home, '.anyscribe'), { recursive: true });
  return { home };
}

async function start(home) {
  const engine = new Engine({
    python,
    home,
    env: logic.buildEnv({ home, packaged: false, tmpdir: os.tmpdir() }),
    log: new AppLog(path.join(home, '.anyscribe', 'logs', 'app.log')),
  });
  engines.push(engine);
  assert.equal(await engine.start(), true, `the engine started: ${JSON.stringify(engine.failure)}`);
  return engine;
}

// The removal, with the real uninstaller; records whether the old engine was alive when it ran.
async function removeWithRealUninstaller(engine, home) {
  const during = {};
  const oldPid = engine.run.child.pid;
  const result = await launcher.removePausingEngine(engine, {
    home,
    platform: 'darwin', // the real uninstaller still runs Linux's own branch here
    python,
    env: engine.env,
    setStartAtLogin: () => {},
    loginItemState: () => 'enabled',
    run: async (cmd, args, opts) => {
      during.oldEngineAlive = alive(oldPid);
      during.args = args;
      const r = await runCapture(cmd, args, opts);
      during.output = r.out.trim();
      return r;
    },
  });
  return { result, during, oldPid };
}

async function assertSurvived(engine, oldPid, during) {
  assert.deepEqual(engine.crashes.exits, [], 'the engine never stopped unexpectedly');
  assert.equal(engine.lastExit, null);
  assert.equal(engine.state, 'running');
  const pid = engine.run.child.pid;
  assert.notEqual(pid, oldPid, 'a new engine');
  assert.equal((await health(engine.port))?.pid, pid, 'the engine on the port is ours');
  assert.equal(during.oldEngineAlive, false, 'the old engine had exited when the uninstall ran');
  assert.deepEqual(during.args, ['-m', 'anyscribe', 'desktop', 'uninstall', '--json']);
}

test('A1: a stale server.pid that names the app engine; the manifest on 8457', { skip: !python && 'set ANYSCRIBE_DEV_PYTHON' }, async () => {
  const { home } = await realEngine();
  fs.writeFileSync(path.join(home, '.anyscribe', 'desktop.json'), JSON.stringify({ port: 8457 }));
  const engine = await start(home);
  const oldPid = engine.run.child.pid;
  // The old launcher's server.pid, reused by the app's engine (alive, and it runs `anyscribe ui`).
  fs.writeFileSync(path.join(home, '.anyscribe', 'server.pid'), String(oldPid));
  const { result, during } = await removeWithRealUninstaller(engine, home);
  await assertSurvived(engine, oldPid, during);
  assert.equal(result.ok, true, JSON.stringify(result));
  assert.equal(fs.existsSync(path.join(home, '.anyscribe', 'desktop.json')), false, 'the real uninstall ran: the manifest is gone');
  assert.equal(fs.existsSync(path.join(home, '.anyscribe', 'server.pid')), false, 'and so is server.pid');
});

// A binary LaunchAgent plist on 8470 (the engine's plistlib reads it), no manifest, and a live
// process with a tray's command line (trayArgs after `tray`) named in tray.pid.
async function binaryPlistFixture(home, trayArgs = []) {
  const plist = launcher.files(home).loginItem;
  fs.mkdirSync(path.dirname(plist), { recursive: true });
  execFileSync(python, ['-c', 'import plistlib, sys; open(sys.argv[1], "wb").write(plistlib.dumps({"Label": "com.anyscribe.tray", "ProgramArguments": ["/py", "-m", "anyscribe", "tray", "--port", "8470"]}, fmt=plistlib.FMT_BINARY))', plist]);
  assert.equal(fs.readFileSync(plist).subarray(0, 8).toString(), 'bplist00', 'a binary plist');
  const env = { ...process.env, HOME: home };
  const enginePort = execFileSync(python, ['-c', 'from anyscribe.core.desktop import installed_port; print(installed_port())'], { env }).toString().trim();
  assert.equal(enginePort, '8470', "the engine's own reading: the old launcher is on 8470");
  const tray = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1 << 30)', '--', '-m', 'anyscribe', 'tray', ...trayArgs], { stdio: 'ignore' });
  started.push(tray);
  await new Promise((r) => tray.once('spawn', r));
  fs.writeFileSync(path.join(home, '.anyscribe', 'tray.pid'), String(tray.pid));
  return tray;
}

test('A2: a binary LaunchAgent plist on 8470 with a live old tray on 8470, no manifest', { skip: !python && 'set ANYSCRIBE_DEV_PYTHON' }, async () => {
  const { home } = await realEngine();
  // The old tray as desktop mode starts it, with its port: the app now avoids 8470 (round 5).
  await binaryPlistFixture(home, ['--port', '8470']);
  const engine = await start(home);
  assert.equal(engine.port, 8471, "the app's engine avoids the old launcher's port");
  const oldPid = engine.run.child.pid;
  const { result, during } = await removeWithRealUninstaller(engine, home);
  await assertSurvived(engine, oldPid, during);
  assert.match(during.output, /"stopped": true/, 'the real uninstall stopped the old tray');
  assert.equal(result.pieces.menuBarIcon, 'stopped');
  if (process.platform === 'darwin') {
    // B3: on a Mac the real uninstall removes this LaunchAgent, so the whole removal succeeds.
    assert.equal(result.pieces.loginItem, 'removed');
    assert.equal(result.ok, true, JSON.stringify(result));
  } else {
    // Elsewhere the engine's uninstall removes its own XDG login item, not this plist.
    assert.equal(result.pieces.loginItem, 'still there');
  }
});

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

test('B2: quitting during a slow uninstall ends it; anyscribe reopened on the same home keeps its engine', { skip: !python && 'set ANYSCRIBE_DEV_PYTHON' }, async (t) => {
  const { home } = await realEngine();
  // This test is about quitting, not ports: it keeps the collision on purpose. The tray names no
  // port, and the plist is treated as unreadable (as on a machine with neither plutil nor XML), so
  // the app's engine lands on the uninstall's target, 8470.
  await binaryPlistFixture(home);
  const realPlutil = launcher.readers.plutil;
  launcher.readers.plutil = () => null;
  t.after(() => (launcher.readers.plutil = realPlutil));
  const first = await start(home);
  assert.equal(first.port, 8470);
  // The real uninstaller, held back: the helper process itself waits until the test says go (at
  // the latest 20 s), so it is what quitting must end, and in the unprotected case it runs only
  // once the new engine answers.
  const go = path.join(ROOT, 'go');
  const slow = path.join(ROOT, 'slow-python');
  fs.writeFileSync(slow, `#!/bin/sh\ni=0\nwhile [ ! -e '${go}' ] && [ $i -lt 200 ]; do sleep 0.1; i=$((i+1)); done\nexec '${python}' "$@"\n`, { mode: 0o755 });
  const removing = launcher.removePausingEngine(first, {
    home,
    platform: 'darwin',
    python: slow,
    env: first.env,
    setStartAtLogin: () => {},
    loginItemState: () => 'enabled',
  });
  const t0 = Date.now();
  while (!first.stepRunning) {
    assert.ok(Date.now() - t0 < 15_000, 'the removal step started');
    await sleep(25);
  }
  await sleep(500); // the uninstaller is waiting
  // What will-quit does.
  first.stopForQuit();
  killHelpers();
  // anyscribe opened again at once on the same home (the quitting app does not wait for anything).
  const second = await start(home);
  assert.equal(second.port, 8470);
  const pid = second.run.child.pid;
  fs.writeFileSync(go, ''); // an uninstaller still alive would run now
  await sleep(6000);
  assert.deepEqual(second.crashes.exits, [], 'the new engine never stopped unexpectedly');
  assert.equal(second.state, 'running');
  assert.equal(second.run.child.pid, pid);
  assert.equal((await health(8470))?.pid, pid, 'the engine on 8470 is the new one');
  await removing;
});
