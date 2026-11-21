// The supervisor two ways: against a real fake engine process (test/fake-engine.js) on the
// real ports 8470/8471, and through its seams (spawn, health, jobs, killGroup) with fake
// children whose fake pids never reach the real process.kill. Tests in this file run one after
// another; they need both ports free. After every test: at most one live child, and no
// "running" status was ever emitted for a child that had exited.
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const EventEmitter = require('node:events');
const fs = require('node:fs');
const http = require('node:http');
const net = require('node:net');
const path = require('node:path');
const { Engine, AppLog, trimLog, pickPort } = require('../src/engine');
const { RESTART_REFUSED, RESTART_UNKNOWN } = require('../src/logic');

const FAKE = path.join(__dirname, 'fake-engine.js');

// Throwaway homes inside the repo (gitignored), removed when the file finishes.
const TMP = path.join(__dirname, '.tmp');
fs.mkdirSync(TMP, { recursive: true });
test.after(() => fs.rmSync(TMP, { recursive: true, force: true }));

function tempHome() {
  return fs.mkdtempSync(path.join(TMP, 'home-'));
}

const hasExited = (child) => child.exitCode !== null || child.signalCode !== null;

// Every engine a test made is checked against the invariants, then stopped.
const made = [];
test.afterEach(async () => {
  for (const { engine, children, violations } of made.splice(0)) {
    const live = children.filter((c) => !hasExited(c));
    await engine.stop();
    assert.ok(live.length <= 1, `at most one live child, saw ${live.length}`);
    assert.deepEqual(violations, [], '"running" only while its child is alive');
  }
});

function watch(engine, children) {
  const violations = [];
  engine.on('status', (s) => {
    if (s.state === 'running' && (!engine.run?.child || hasExited(engine.run.child))) violations.push('running with no live child');
  });
  made.push({ engine, children, violations });
}

// A real fake engine process.
function makeEngine(fakeEnv = {}, opts = {}) {
  const home = tempHome();
  const log = new AppLog(path.join(home, '.anyscribe', 'logs', 'app.log'));
  const children = [];
  const engine = new Engine({
    python: process.execPath,
    prefixArgs: [FAKE],
    home,
    env: { HOME: home, PATH: process.env.PATH, ...fakeEnv },
    log,
    stopWaitMs: 1000,
    spawn: (...args) => {
      const child = childProcess.spawn(...args);
      children.push(child);
      return child;
    },
    ...opts,
  });
  watch(engine, children);
  return { engine, home, log, children };
}

// Fake children and seams: nothing real is spawned, fetched or signalled.
let nextFakePid = 90_000_000; // above any real pid_max
class FakeChild extends EventEmitter {
  constructor() {
    super();
    this.pid = nextFakePid++;
    this.exitCode = null;
    this.signalCode = null;
    this.stdin = Object.assign(new EventEmitter(), { ended: false, end() { this.ended = true; } });
    this.stdout = new EventEmitter();
    this.stderr = new EventEmitter();
  }
  exit(code, signal = null) {
    if (hasExited(this)) return;
    this.exitCode = code;
    this.signalCode = signal;
    this.emit('exit', code, signal);
  }
}

function deferred() {
  let resolve;
  const promise = new Promise((r) => (resolve = r));
  return { promise, resolve };
}

function makeSeamEngine({ ignoreSignals = false, health, jobs, home = tempHome(), log, ...opts } = {}) {
  const children = [];
  const kills = [];
  const engine = new Engine({
    python: '/nonexistent/python',
    home,
    env: {},
    log: log ?? new AppLog(path.join(home, '.anyscribe', 'logs', 'app.log')),
    stopWaitMs: 50,
    spawn: () => {
      const child = new FakeChild();
      children.push(child);
      return child;
    },
    health: health ?? (async () => ({ app: 'anyscribe', pid: children.at(-1)?.pid })),
    jobs: jobs ?? (async () => []),
    killGroup: (pid, signal) => {
      kills.push([pid, signal]);
      const child = children.find((c) => c.pid === pid);
      if (child && !ignoreSignals) setImmediate(() => child.exit(null, signal));
    },
    ...opts,
  });
  watch(engine, children);
  return { engine, children, kills, home };
}

const alive = (pid) => {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function waitFor(predicate, ms = 10_000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const tick = () => {
      if (predicate()) return resolve();
      if (Date.now() - start > ms) return reject(new Error(`timed out after ${ms} ms`));
      setTimeout(tick, 25);
    };
    tick();
  });
}

function listen(port) {
  return new Promise((resolve) => {
    const srv = net.createServer((s) => s.destroy());
    srv.listen(port, '127.0.0.1', () => resolve(srv));
  });
}

test('pickPort: 8470, 8471 beside the old desktop mode, and a taken port', async () => {
  const home = tempHome();
  assert.deepEqual(await pickPort(home), { port: 8470, taken: false });
  fs.mkdirSync(path.join(home, '.anyscribe'), { recursive: true });
  fs.writeFileSync(path.join(home, '.anyscribe', 'desktop.json'), JSON.stringify({ port: 8470 }));
  assert.deepEqual(await pickPort(home), { port: 8471, taken: false });
  const srv = await listen(8471);
  try {
    assert.deepEqual(await pickPort(home), { port: 8471, taken: true });
  } finally {
    srv.close();
  }
});

test('starts, answers, and stops by its own pid', async () => {
  const { engine, log } = makeEngine();
  assert.equal(await engine.start(), true);
  assert.deepEqual(engine.status(), { state: 'running', port: 8470, lastExit: null, stoppedRestarting: false });
  const pid = engine.run.child.pid;
  assert.ok(alive(pid));
  await engine.stop();
  assert.equal(engine.status().state, 'stopped');
  assert.equal(alive(pid), false);
  assert.match(log.tail().join('\n'), /engine started \(pid \d+, port 8470\)[\s\S]*engine stopped/);
});

test('guard: a taken port is refused, nothing is started on it', async () => {
  const srv = await listen(8470);
  try {
    const { engine, log } = makeEngine();
    assert.equal(await engine.start(), false);
    assert.equal(engine.status().state, 'stopped');
    assert.equal(engine.failure.kind, 'port');
    assert.equal(engine.lastExit.reason, 'another program is using port 8470');
    assert.ok(!log.tail().some((l) => l.includes('engine started')), 'no engine was spawned');
  } finally {
    srv.close();
  }
});

test('an engine that exits early: reason and log lines for the start window', async () => {
  const { engine } = makeEngine({ FAKE_MODE: 'exit-early' });
  assert.equal(await engine.start(), false);
  assert.equal(engine.failure.kind, 'exited');
  assert.equal(engine.lastExit.code, 1);
  assert.match(engine.lastExit.reason, /^PermissionError: \[Errno 13\]/);
  assert.match(engine.failure.lines[0], /^engine exited with code 1 after \d+\.\d s$/);
  assert.equal(engine.failure.lines.at(-1), 'log: ~/.anyscribe/logs/app.log');
});

test('no answer within the time limit: stopped with no reason, child killed', async () => {
  const { engine } = makeEngine({ FAKE_MODE: 'silent' }, { readyTimeoutMs: 600 });
  const started = engine.start();
  await waitFor(() => engine.run?.child);
  const pid = engine.run.child.pid;
  assert.equal(await started, false);
  assert.equal(engine.failure.kind, 'timeout');
  assert.equal(engine.lastExit.reason, null);
  await waitFor(() => !alive(pid), 3000);
});

test('guard: three unexpected exits within a minute stop the retries', async () => {
  const { engine, log } = makeEngine({ FAKE_MODE: 'crash' });
  const states = [];
  engine.on('status', (s) => states.push(s.state));
  await engine.start();
  await waitFor(() => engine.stoppedRestarting, 10_000);
  await new Promise((r) => setTimeout(r, 800)); // would a fourth start follow?
  assert.equal(engine.status().state, 'stopped');
  assert.equal(engine.failure.kind, 'crashes');
  assert.deepEqual(engine.lastExit, { code: 1, signal: null, reason: null });
  assert.equal(log.tail().filter((l) => l.includes('engine started')).length, 3);
  assert.deepEqual(states, ['starting', 'running', 'restarting', 'running', 'restarting', 'running', 'stopped']);
});

test('guard: Restart engine is refused while a job is pending or running', async () => {
  const jobs = [{ job_id: 'a', status: 'running', stage: 'transcribe', url: 'u', title: null }];
  const { engine } = makeEngine({ FAKE_JOBS: JSON.stringify(jobs) });
  await engine.start();
  const pid = engine.run.child.pid;
  assert.deepEqual(await engine.restart(), { ok: false, reason: RESTART_REFUSED });
  assert.equal(engine.run.child.pid, pid, 'the same engine is still running');
  await engine.stop();
});

test('Restart engine with no jobs restarts it', async () => {
  const { engine } = makeEngine({ FAKE_JOBS: '[]' });
  await engine.start();
  const pid = engine.run.child.pid;
  assert.deepEqual(await engine.jobs(), []);
  assert.deepEqual(await engine.restart(), { ok: true, reason: null });
  assert.notEqual(engine.run.child.pid, pid);
  assert.equal(alive(pid), false);
  await engine.stop();
});

test('log: over 5 MB at launch keeps the last 1 MB from a whole line', () => {
  const file = path.join(tempHome(), 'app.log');
  const line = `${'x'.repeat(99)}\n`;
  fs.writeFileSync(file, `${line.repeat(60_000)}last line\n`);
  trimLog(file);
  const kept = fs.readFileSync(file, 'utf8');
  assert.ok(kept.length <= 1024 * 1024 && kept.length > 1024 * 1024 - 200);
  assert.ok(kept.startsWith('x'.repeat(99) + '\n'));
  assert.ok(kept.endsWith('last line\n'));
  fs.writeFileSync(file, 'small\n');
  trimLog(file);
  assert.equal(fs.readFileSync(file, 'utf8'), 'small\n');
});

test('the add-ons folder is made for the packaged Python only (F10)', async () => {
  const site = (home) => path.join(home, '.anyscribe', 'runtime', 'lib', 'python3.13', 'site-packages');
  const dev = makeEngine();
  await dev.engine.start();
  assert.equal(fs.existsSync(site(dev.home)), false);
  await dev.engine.stop();
  const packaged = makeEngine({}, { packaged: true });
  await packaged.engine.start();
  assert.equal(fs.existsSync(site(packaged.home)), true);
});

test('jobs: a list that cannot be read is unknown (null), never empty (C1)', async () => {
  const cases = [
    ['timeout', { FAKE_JOBS: '[]', FAKE_JOBS_DELAY_MS: '3000' }],
    ['HTTP 500', { FAKE_JOBS: '[]', FAKE_JOBS_STATUS: '500' }],
    ['404', {}],
    ['bad JSON', { FAKE_JOBS: 'not json' }],
    ['{"jobs":{}}', { FAKE_JOBS: '{"jobs":{}}' }],
    ['[null]', { FAKE_JOBS: '[null]' }],
  ];
  for (const [name, env] of cases) {
    const { engine } = makeEngine(env);
    await engine.start();
    assert.equal(await engine.jobs(), null, name);
    await engine.stop();
  }
  const { engine } = makeEngine({ FAKE_JOBS: '[]' });
  await engine.start();
  assert.deepEqual(await engine.jobs(), [], 'a real empty list is known');
});

test('Restart engine is refused while the job list is unknown', async () => {
  const { engine } = makeEngine({ FAKE_JOBS: '[]', FAKE_JOBS_STATUS: '500' });
  await engine.start();
  const pid = engine.run.child.pid;
  assert.deepEqual(await engine.restart(), { ok: false, reason: RESTART_UNKNOWN });
  assert.equal(engine.run.child.pid, pid);
});

test('stopForQuit: closes stdin and SIGTERMs its own child at once', async () => {
  const { engine } = makeEngine();
  await engine.start();
  const child = engine.run.child;
  engine.stopForQuit();
  await waitFor(() => child.exitCode !== null || child.signalCode !== null, 3000);
});

test('guard: a server answering with another pid is not ours (C2)', async () => {
  const { engine, log } = makeEngine({ FAKE_MODE: 'impostor' });
  const started = engine.start();
  await waitFor(() => engine.run?.child);
  const pid = engine.run.child.pid;
  assert.equal(await started, false);
  assert.equal(engine.failure.kind, 'port');
  assert.equal(engine.lastExit.reason, 'another program is using port 8470');
  assert.equal(engine.run, null);
  await waitFor(() => !alive(pid), 3000);
  assert.ok(!log.tail().some((l) => l.includes('engine ready')));
});

test('a stop during start sends nothing to a server that is not ours (C2, A2)', async () => {
  const { engine } = makeEngine({ FAKE_MODE: 'silent' });
  const started = engine.start();
  await waitFor(() => engine.run?.child);
  const requests = [];
  const other = http.createServer((req, res) => {
    requests.push(`${req.method} ${req.url}`);
    res.statusCode = 404;
    res.end();
  });
  await new Promise((r) => other.listen(8470, '127.0.0.1', r));
  try {
    await sleep(300);
    await engine.stop();
    await started;
    assert.ok(!requests.some((r) => r.startsWith('POST')), requests.join(', '));
  } finally {
    other.close();
  }
});

const startedPids = (log) => log.tail(400).flatMap((l) => [...l.matchAll(/engine started \(pid (\d+)/g)].map((m) => Number(m[1])));

test('guard: a second restart while one is pending is refused; one engine, and it is ours (C4, A4)', async () => {
  const { engine, log } = makeEngine({ FAKE_JOBS: '[]' });
  await engine.start();
  const results = await Promise.all([engine.restart(), engine.restart()]);
  assert.deepEqual(results, [{ ok: true, reason: null }, { ok: false, reason: 'A restart is already under way.' }]);
  const pids = startedPids(log);
  assert.equal(pids.length, 2);
  assert.deepEqual(pids.filter(alive), [engine.run.child.pid], 'only the last engine is alive, and the shell holds it');
});

test('guard: a stop while restarting after a crash starts nothing new (F3)', async () => {
  const { engine, log } = makeEngine({ FAKE_MODE: 'crash' });
  let stopped;
  engine.on('status', (s) => {
    if (s.state === 'restarting' && !stopped) stopped = engine.stop();
  });
  await engine.start();
  await waitFor(() => stopped, 5000);
  await stopped;
  await sleep(1000);
  assert.equal(engine.status().state, 'stopped');
  assert.equal(engine.run, null);
  assert.deepEqual(startedPids(log).filter(alive), [], 'no engine left running');
  assert.equal(startedPids(log).length, 1, 'no engine started after the stop');
});

test('guard: a stop during the port check spawns nothing (F3)', async () => {
  const { engine, log } = makeEngine();
  let stopped;
  engine.on('status', (s) => {
    if (s.state === 'starting' && !stopped) stopped = engine.stop();
  });
  assert.equal(await engine.start(), false);
  await stopped;
  await sleep(300);
  assert.equal(engine.failure, null, 'the port was free: nothing but the stop kept the engine from starting');
  assert.deepEqual(startedPids(log), []);
  assert.equal(engine.status().state, 'stopped');
});

test("guard: an unwritable log folder shows couldn't start, never throws (C9)", async () => {
  const home = tempHome();
  fs.mkdirSync(path.join(home, '.anyscribe'), { recursive: true });
  fs.writeFileSync(path.join(home, '.anyscribe', 'logs'), 'a file where the log folder should be');
  const log = new AppLog(path.join(home, '.anyscribe', 'logs', 'app.log'));
  assert.match(log.error, /EEXIST|ENOTDIR/);
  log.shell('still kept in memory');
  assert.match(log.tail().at(-1), /still kept in memory/);
  const engine = new Engine({ python: process.execPath, prefixArgs: [FAKE], home, env: { HOME: home, PATH: process.env.PATH }, log });
  watch(engine, []);
  assert.equal(await engine.start(), false);
  assert.equal(engine.failure.kind, 'log');
  assert.match(engine.lastExit.reason, /^Can't write the log file: /);
  assert.equal(engine.run, null, 'no engine started without a log');
});

test('guard: stop takes the engine\'s helpers with it (its process group) (S-design-C)', async () => {
  const { engine, log } = makeEngine({ FAKE_MODE: 'stubborn', FAKE_GRANDCHILD: '1' }, { stopWaitMs: 500 });
  let grandchild;
  try {
    await engine.start();
    await waitFor(() => /grandchild pid (\d+)/.test(log.tail().join('\n')), 3000);
    grandchild = Number(log.tail().join('\n').match(/grandchild pid (\d+)/)[1]);
    const pid = engine.run.child.pid;
    assert.ok(alive(grandchild));
    await engine.stop();
    assert.equal(alive(pid), false, 'the engine is gone');
    await waitFor(() => !alive(grandchild), 2000).catch(() => {});
    assert.equal(alive(grandchild), false, `its helper (pid ${grandchild}) is gone too`);
  } finally {
    if (grandchild && alive(grandchild)) process.kill(grandchild, 'SIGKILL'); // the pid this test read
  }
});

test("guard: a crashed engine's helpers are stopped with its group (S-open-3)", async () => {
  const { engine, log } = makeEngine({ FAKE_MODE: 'crash', FAKE_GRANDCHILD: '1' });
  const helpers = () => [...log.tail(400).join('\n').matchAll(/grandchild pid (\d+)/g)].map((m) => Number(m[1]));
  try {
    await engine.start();
    await waitFor(() => engine.stoppedRestarting, 10_000);
    assert.equal(helpers().length, 3, 'one helper per engine start');
    await waitFor(() => !helpers().some(alive), 3000).catch(() => {});
    assert.deepEqual(helpers().filter(alive), [], 'no helper outlives its crashed engine');
  } finally {
    for (const pid of helpers()) if (alive(pid)) process.kill(pid, 'SIGKILL'); // pids this test read
  }
});

// ---- round 3: the design's tests, through the seams ----

test('guard: a health answer that arrives after the child exited is dropped (A1)', async () => {
  const reply = deferred();
  const { engine, children } = makeSeamEngine({ health: () => reply.promise });
  const states = [];
  engine.on('status', (s) => states.push(s.state));
  const started = engine.start();
  await waitFor(() => children.length === 1);
  await sleep(20); // the health request is now held open
  children[0].exit(1);
  reply.resolve({ app: 'anyscribe', pid: children[0].pid }); // "ours", too late
  assert.equal(await started, false);
  await sleep(20);
  assert.ok(!states.includes('running'), `states: ${states.join(', ')}`);
  assert.equal(engine.state, 'stopped');
  assert.equal(engine.failure.kind, 'exited');
});

for (const how of ['stop', 'stopForQuit']) {
  test(`guard: a restart whose job read is overtaken by ${how}() starts nothing (A4)`, async () => {
    const list = deferred();
    let held = false;
    const { engine, children } = makeSeamEngine({ jobs: () => ((held = true), list.promise) });
    assert.equal(await engine.start(), true);
    const restarting = engine.restart();
    await waitFor(() => held);
    const stopped = how === 'stop' ? engine.stop() : engine.stopForQuit();
    list.resolve([]);
    assert.deepEqual(await restarting, { ok: false, reason: 'The engine was stopped while the restart was being checked.' });
    await stopped;
    await sleep(20);
    assert.equal(children.length, 1, 'no second engine');
    assert.equal(engine.state, 'stopped');
  });
}

test('guard: stop sends no HTTP; stdin, SIGTERM to the group, then SIGKILL after the wait (A2)', async () => {
  const { engine, children, kills } = makeSeamEngine({ ignoreSignals: true });
  assert.equal(await engine.start(), true);
  const child = children[0];
  const realFetch = globalThis.fetch;
  const fetched = [];
  globalThis.fetch = (...args) => (fetched.push(String(args[0])), realFetch(...args));
  try {
    const stopped = engine.stop();
    assert.equal(child.stdin.ended, true, 'stdin closed');
    assert.deepEqual(kills, [[child.pid, 'SIGTERM']], 'SIGTERM to the group at once');
    await sleep(120);
    assert.deepEqual(kills, [[child.pid, 'SIGTERM'], [child.pid, 'SIGKILL']], 'SIGKILL to the group after the wait');
    child.exit(null, 'SIGKILL');
    await stopped;
    assert.deepEqual(fetched, [], 'no request at all during the stop');
    assert.equal(engine.state, 'stopped');
  } finally {
    globalThis.fetch = realFetch;
  }
});

test('guard: an unwritable app.log stops the start; Try again after a repair starts it (A3, G6)', async () => {
  const home = tempHome();
  const file = path.join(home, '.anyscribe', 'logs', 'app.log');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, '');
  fs.chmodSync(file, 0o444);
  const log = new AppLog(file);
  assert.equal(log.error, null, 'the folder and size checks pass: only an append can tell');
  const { engine, children } = makeSeamEngine({ home, log });
  try {
    assert.equal(await engine.start(), false);
    assert.equal(children.length, 0, 'nothing spawned');
    assert.equal(engine.failure.kind, 'log');
    assert.match(engine.lastExit.reason, /^Can't write the log file: EACCES/);
    fs.chmodSync(file, 0o644);
    assert.equal(await engine.start(), true, 'Try again');
    assert.equal(children.length, 1);
    assert.match(fs.readFileSync(file, 'utf8'), /engine started \(pid \d+, port 8470\)/);
  } finally {
    fs.chmodSync(file, 0o644);
  }
});

test('guard: an engine that dies before it is ready leaves no helper behind (R2)', async () => {
  const { engine, log } = makeEngine({ FAKE_MODE: 'die-before-ready', FAKE_GRANDCHILD: '1' });
  let helper;
  try {
    assert.equal(await engine.start(), false);
    helper = Number(log.tail().join('\n').match(/grandchild pid (\d+)/)[1]);
    assert.equal(engine.failure.kind, 'exited');
    await waitFor(() => !alive(helper), 2000).catch(() => {});
    assert.equal(alive(helper), false, `helper pid ${helper} is gone`);
  } finally {
    if (helper && alive(helper)) process.kill(helper, 'SIGKILL'); // the pid this test read
  }
});

test('guard: an explicit stop during a restart cancels its relaunch (S3-A1)', async () => {
  const { engine, children, kills } = makeSeamEngine({ ignoreSignals: true });
  assert.equal(await engine.start(), true);
  const old = children[0];
  const restarting = engine.restart();
  await waitFor(() => kills.some(([pid, sig]) => pid === old.pid && sig === 'SIGTERM'));
  const stopped = engine.stop();
  old.exit(null, 'SIGTERM');
  const result = await restarting;
  await stopped;
  await sleep(20);
  assert.equal(result.ok, false, 'the overtaken restart reports it did not restart');
  assert.equal(children.length, 1, 'no second engine');
  assert.equal(engine.run, null);
  assert.equal(engine.state, 'stopped');
});
