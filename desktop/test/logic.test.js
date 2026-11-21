'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const logic = require('../src/logic');

const job = (status, extra = {}) => ({ job_id: Math.random().toString(36).slice(2), url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw', status, stage: null, title: null, completed_at: null, ...extra });

test('port: 8470 unless the old desktop mode records 8470', () => {
  assert.equal(logic.choosePort(null), 8470);
  assert.equal(logic.choosePort(8457), 8470);
  assert.equal(logic.choosePort(8470), 8471);
});

test('python: packaged uses the bundled one, dev needs ANYSCRIBE_DEV_PYTHON', () => {
  assert.equal(logic.resolvePython({ packaged: true, resourcesPath: '/A/Resources', env: {} }), '/A/Resources/python/bin/python3');
  assert.equal(logic.resolvePython({ packaged: false, env: { ANYSCRIBE_DEV_PYTHON: '/v/bin/python' }, cwd: '/x' }), '/v/bin/python');
  // C6: a relative path is resolved against where the app started, not the engine's HOME.
  assert.equal(logic.resolvePython({ packaged: false, env: { ANYSCRIBE_DEV_PYTHON: '../.venv/bin/python' }, cwd: '/repo/desktop' }), '/repo/.venv/bin/python');
  assert.equal(logic.resolvePython({ packaged: false, env: { ANYSCRIBE_DEV_PYTHON: 'python3' }, cwd: '/repo/desktop' }), 'python3');
  assert.throws(() => logic.resolvePython({ packaged: false, env: {} }), /ANYSCRIBE_DEV_PYTHON/);
});

test('environment: packaged PATH is the app bin plus system dirs, never the caller PATH', () => {
  const saved = process.env.PATH;
  process.env.PATH = '/caller/only/bin:/usr/bin';
  try {
    const env = logic.buildEnv({ home: '/Users/u', packaged: true, resourcesPath: '/A/Resources', execPath: '/A/MacOS/anyscribe', tmpdir: '/tmp/x' });
    assert.equal(env.PATH, '/A/Resources/bin:/usr/bin:/bin:/usr/sbin:/sbin');
    assert.ok(!env.PATH.includes('/caller/only/bin'));
    assert.deepEqual(env, {
      HOME: '/Users/u',
      PATH: '/A/Resources/bin:/usr/bin:/bin:/usr/sbin:/sbin',
      ANYSCRIBE_APP: '1',
      PYTHONUSERBASE: '/Users/u/.anyscribe/runtime',
      PIP_USER: '1',
      LANG: 'en_US.UTF-8',
      PYTHONUNBUFFERED: '1',
      TMPDIR: '/tmp/x',
      ANYSCRIBE_ELECTRON: '/A/MacOS/anyscribe',
    });
    const dev = logic.buildEnv({ home: '/Users/u', packaged: false, execPath: '/e', tmpdir: '/tmp/x' });
    assert.equal(dev.PATH, '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin');
    assert.equal(dev.ANYSCRIBE_ELECTRON, undefined);
  } finally {
    process.env.PATH = saved;
  }
});

test('engine args always carry --watch-stdin', () => {
  assert.deepEqual(logic.engineArgs(8470), ['-m', 'anyscribe', 'ui', '--port', '8470', '--no-open', '--watch-stdin']);
});

test('menu: Ready', () => {
  assert.deepEqual(logic.menuModel({ engineState: 'running', jobs: [] }), {
    icon: 'plain',
    header: 'anyscribe · Ready',
    rows: [],
    actions: ['open', 'startAtLogin', 'quit'],
  });
});

test('menu: Transcribing, with titles, links and stage words', () => {
  const jobs = [
    job('running', { title: 'Founder interview, part 2', stage: 'transcribe' }),
    job('running', { stage: 'download' }),
    job('pending', { url: 'https://www.instagram.com/reel/C0abcdefghijk/' }),
    job('completed', { title: 'Done earlier', completed_at: 1 }),
  ];
  const m = logic.menuModel({ engineState: 'running', jobs });
  assert.equal(m.header, 'Transcribing · 2 running, 1 waiting');
  assert.equal(m.icon, 'working');
  assert.deepEqual(m.rows, [
    { label: 'Founder interview, part 2', stage: 'Transcribing' },
    { label: 'youtube.com/watch?v=jNQX…', stage: 'Downloading' },
    { label: 'instagram.com/reel/C0abc…', stage: 'Waiting' },
  ]);
  assert.deepEqual(m.actions, ['open', 'startAtLogin', 'quit']);
  for (const [stage, word] of [['write', 'Saving'], ['index', 'Saving'], ['cached', 'Saving'], [null, 'Downloading']]) {
    assert.equal(logic.stageWord(job('running', { stage })), word);
  }
});

test('menu: Finished while the window was closed (kept until shown)', () => {
  const hiddenSince = Date.parse('2026-11-20T14:00:00Z');
  const jobs = [
    job('completed', { title: 'Founder interview, part 2', completed_at: hiddenSince / 1000 + 60 }),
    job('failed', { completed_at: '2026-11-20T14:02:00Z' }),
    job('completed', { title: 'Before closing', completed_at: hiddenSince / 1000 - 60 }),
    job('cancelled', { completed_at: hiddenSince / 1000 + 5 }),
  ];
  const finished = [...logic.rememberFinished(new Map(), jobs, hiddenSince).values()];
  const m = logic.menuModel({ engineState: 'running', jobs, finished });
  assert.equal(m.header, 'anyscribe · 1 saved, 1 failed');
  assert.equal(m.icon, 'alert');
  assert.deepEqual(m.rows, [
    { label: 'youtube.com/watch?v=jNQX…', stage: 'Failed' },
    { label: 'Founder interview, part 2', stage: 'Saved' },
  ], 'newest first');
  // Window shown again: forgotten, back to Ready.
  assert.equal(logic.rememberFinished(new Map(finished.map((j) => [j.job_id, j])), jobs, null).size, 0);
  assert.equal(logic.menuModel({ engineState: 'running', jobs, finished: [] }).header, 'anyscribe · Ready');
  // Saved only: no red dot.
  assert.equal(logic.menuModel({ engineState: 'running', jobs, finished: finished.slice(0, 1) }).icon, 'plain');
});

test('guard: a failure stays in the menu after 50 later completions push it off the list (C7)', () => {
  const hiddenSince = Date.parse('2026-11-20T14:00:00Z');
  const failure = job('failed', { job_id: 'the-failure', completed_at: hiddenSince / 1000 + 1 });
  let memory = logic.rememberFinished(new Map(), [failure], hiddenSince); // poll 1
  const fifty = Array.from({ length: 50 }, (_, i) => job('completed', { title: `Saved ${i}`, completed_at: hiddenSince / 1000 + 10 + i }));
  memory = logic.rememberFinished(memory, fifty, hiddenSince); // poll 2: the engine's 50 rows no longer hold it
  const m = logic.menuModel({ engineState: 'running', jobs: fifty, finished: [...memory.values()] });
  assert.equal(m.icon, 'alert');
  assert.equal(m.header, 'anyscribe · 50 saved, 1 failed');
});

test("menu: Engine stopped · couldn't restart offers Restart engine", () => {
  const m = logic.menuModel({ engineState: 'stopped', stoppedRestarting: true, jobs: [] });
  assert.equal(m.header, "Engine stopped · couldn't restart");
  assert.equal(m.icon, 'alert');
  assert.deepEqual(m.actions, ['restartEngine', 'open', 'startAtLogin', 'quit']);
});

test('menu: Quitting when these finish', () => {
  const jobs = [job('running', { title: 'Founder interview, part 2', stage: 'write' }), job('pending')];
  const m = logic.menuModel({ engineState: 'running', jobs, quitWhenDone: true });
  assert.equal(m.header, 'Quitting when these finish');
  assert.deepEqual(m.rows, [
    { label: 'Founder interview, part 2', stage: 'Saving' },
    { label: 'youtube.com/watch?v=jNQX…', stage: 'Waiting' },
  ]);
  assert.deepEqual(m.actions, ['dontQuit', 'stopAndQuit']);
});

test('quit question: wording and counts', () => {
  const q = logic.quitQuestion([job('running'), job('running'), job('pending'), job('completed')]);
  assert.equal(q.message, 'Transcriptions are still running');
  assert.equal(q.detail, '2 are running and 1 is waiting. Quit when they finish, or stop them now? To finish a stopped one later, transcribe it again.');
  assert.deepEqual(q.buttons, ['Quit When Done', 'Stop and Quit', 'Cancel']);
  assert.equal(q.defaultId, 0);
  assert.equal(q.cancelId, 2);
  assert.match(logic.quitQuestion([job('running')]).detail, /^1 is running\. Quit/);
  assert.match(logic.quitQuestion([job('pending'), job('pending')]).detail, /^2 are waiting\. Quit/);
  assert.equal(logic.quitQuestion([job('completed'), job('failed'), job('cancelled')]), null);
});

test('quit: decided at once from the last poll (C1, F1, F2)', () => {
  const idle = logic.quitDecision({ running: true, known: true, jobs: [job('completed')] });
  assert.equal(idle, null, 'known and idle: the quit is not prevented');
  assert.equal(logic.quitDecision({ running: false, known: false, jobs: [] }), null, 'no engine: quit');
  const busy = logic.quitDecision({ running: true, known: true, jobs: [job('running')] });
  assert.equal(busy.box.message, 'Transcriptions are still running');
  assert.deepEqual(busy.choices, ['whenDone', 'stopAndQuit', 'cancel']);
  const unknown = logic.quitDecision({ running: true, known: false, jobs: [] });
  assert.deepEqual(unknown.box, {
    type: 'question',
    message: "anyscribe couldn't check which transcriptions are running",
    detail: 'Quit when they finish, or stop them now? To finish a stopped one later, transcribe it again.',
    buttons: ['Quit When Done', 'Stop and Quit', 'Cancel'],
    defaultId: 0,
    cancelId: 2,
  });
  assert.deepEqual(unknown.choices, ['whenDone', 'stopAndQuit', 'cancel'], 'G4: the approved three buttons');
});

test('Quit When Done waits while the list is unknown', () => {
  assert.equal(logic.quitWhenDoneReady({ known: false, jobs: [] }), false);
  assert.equal(logic.quitWhenDoneReady({ known: true, jobs: [job('pending')] }), false);
  assert.equal(logic.quitWhenDoneReady({ known: true, jobs: [job('completed')] }), true);
});

test('job list shape: anything else is unknown, never empty', () => {
  const good = [job('running')];
  assert.equal(logic.validJobs(good), good);
  assert.deepEqual(logic.validJobs([]), []);
  for (const bad of [{ jobs: {} }, { jobs: [] }, [null], [{ job_id: 1, status: 'running' }], [{ job_id: 'a' }], null, 'x']) {
    assert.equal(logic.validJobs(bad), null, JSON.stringify(bad));
  }
});

test('restart refusal while any job is pending or running', () => {
  assert.equal(logic.restartRefusal([job('running')]), 'Wait for transcriptions to finish before restarting the engine.');
  assert.equal(logic.restartRefusal([job('pending')]), logic.RESTART_REFUSED);
  assert.equal(logic.restartRefusal([job('completed'), job('failed')]), null);
  assert.equal(logic.restartRefusal(null), "anyscribe couldn't check for running transcriptions; try again in a moment");
});

test('crash window: the third exit within 60 s stops retrying', () => {
  const w = new logic.CrashWindow();
  assert.equal(w.record(0), false);
  assert.equal(w.record(30_000), false);
  assert.equal(w.record(59_999), true);
  const spread = new logic.CrashWindow();
  assert.equal(spread.record(0), false);
  assert.equal(spread.record(30_000), false);
  assert.equal(spread.record(60_001), false, 'the first exit fell out of the minute');
  assert.equal(spread.record(61_000), true);
});

test("start window: the couldn't-start sentence for each reason", () => {
  const safe = 'Your transcripts and settings are safe.';
  assert.equal(logic.failureMessage({ kind: 'port', reason: 'another program is using port 8470' }), `Its engine couldn't start: another program is using port 8470. ${safe}`);
  assert.equal(logic.failureMessage({ kind: 'timeout' }), `Its engine didn't answer within a minute. ${safe}`);
  assert.equal(logic.failureMessage({ kind: 'exited', reason: 'PermissionError: x' }), `Its engine stopped before it was ready. ${safe}`);
  assert.equal(logic.failureMessage({ kind: 'log', reason: "Can't write the log file: EACCES" }), `Can't write the log file: EACCES. ${safe}`);
  assert.equal(logic.failureMessage({ kind: 'crashes' }), `Its engine stopped 3 times in a minute, so anyscribe stopped restarting it. ${safe}`);
});

test('links: the app keeps its own pages; other origins never load inside it (C3)', () => {
  const ours = ['http://127.0.0.1:8470/'];
  const start = 'file:///app/src/start.html';
  const nav = (url, main = true) => logic.navigation(url, ours, start, main);
  assert.equal(nav('http://127.0.0.1:8470/history'), 'allow');
  assert.equal(nav(start), 'allow');
  assert.equal(nav('https://github.com/rishmadaan/anyscribe'), 'outside', 'a link or redirect out opens in the browser');
  assert.equal(nav('http://127.0.0.1:8470.evil.example/'), 'outside');
  assert.equal(nav('http://127.0.0.1:9999/'), 'outside', 'another local port is not ours');
  assert.equal(nav('https://evil.example/', false), 'block', 'an outside iframe is blocked, not opened');
  assert.equal(nav('about:blank', false), 'allow');
  assert.equal(nav('about:blank', true), 'block');
  assert.equal(nav('file:///etc/passwd'), 'block');
  assert.equal(nav('javascript:alert(1)'), 'block');
});

test('menu layout matches mockup section 6: separators and header (F6)', () => {
  const layout = (m) => logic.menuLayout(m).join(' ');
  assert.equal(layout(logic.menuModel({ engineState: 'running', jobs: [] })), 'header open separator startAtLogin separator quit');
  assert.equal(
    layout(logic.menuModel({ engineState: 'running', jobs: [job('running'), job('pending')] })),
    'header row row separator open separator startAtLogin separator quit'
  );
  assert.equal(
    layout(logic.menuModel({ engineState: 'stopped', stoppedRestarting: true })),
    'header restartEngine open separator startAtLogin separator quit'
  );
  assert.equal(
    layout(logic.menuModel({ engineState: 'running', jobs: [job('running')], quitWhenDone: true })),
    'header row separator dontQuit stopAndQuit'
  );
});

test('menu: finished-while-closed shows failed first, then the newest, 5 rows, then "and N more" (S-open-4, G1)', () => {
  const hiddenSince = Date.parse('2026-11-20T14:00:00Z');
  const done = Array.from({ length: 7 }, (_, i) =>
    job(i === 0 ? 'failed' : 'completed', { title: `Job ${i}`, completed_at: hiddenSince / 1000 + 10 * (i + 1) })
  );
  const m = logic.menuModel({ engineState: 'running', jobs: [], finished: done });
  assert.equal(m.header, 'anyscribe · 6 saved, 1 failed', 'the header counts all seven');
  assert.equal(m.icon, 'alert');
  assert.deepEqual(m.rows, [
    { label: 'Job 0', stage: 'Failed' }, // the oldest, but the one he needs
    { label: 'Job 6', stage: 'Saved' },
    { label: 'Job 5', stage: 'Saved' },
    { label: 'Job 4', stage: 'Saved' },
    { label: 'Job 3', stage: 'Saved' },
    { label: 'and 2 more finished', stage: null },
  ]);
  assert.equal(logic.menuLayout(m).filter((x) => x === 'row').length, 6);
});

test('menu: waiting rows are capped at 5 plus "and N more"; running rows always shown (G3)', () => {
  const jobs = [job('running', { title: 'A', stage: 'transcribe' }), job('running', { title: 'B', stage: 'download' })];
  for (let i = 0; i < 10; i++) jobs.push(job('pending', { title: `W${i}` }));
  const expected = [
    { label: 'A', stage: 'Transcribing' },
    { label: 'B', stage: 'Downloading' },
    ...[0, 1, 2, 3, 4].map((i) => ({ label: `W${i}`, stage: 'Waiting' })),
    { label: 'and 5 more waiting', stage: null },
  ];
  const m = logic.menuModel({ engineState: 'running', jobs });
  assert.equal(m.header, 'Transcribing · 2 running, 10 waiting');
  assert.deepEqual(m.rows, expected);
  assert.deepEqual(logic.menuModel({ engineState: 'running', jobs, quitWhenDone: true }).rows, expected);
});

test('menu: the header says "not answering" from the third failed read in a row (G4)', () => {
  const jobs = [job('running', { title: 'A', stage: 'transcribe' })];
  assert.equal(logic.menuModel({ engineState: 'running', jobs, failedReads: 2 }).header, 'Transcribing · 1 running');
  assert.equal(logic.menuModel({ engineState: 'running', jobs, failedReads: 3 }).header, 'Transcribing · 1 running · not answering');
  assert.equal(logic.menuModel({ engineState: 'running', jobs: [], failedReads: 5 }).header, 'anyscribe · Not answering', 'G9: idle reads Not answering, not Ready');
  assert.equal(logic.menuModel({ engineState: 'running', jobs, failedReads: 3, quitWhenDone: true }).header, 'Quitting when these finish · not answering');
  assert.equal(logic.menuModel({ engineState: 'stopped', stoppedRestarting: true, failedReads: 5 }).header, "Engine stopped · couldn't restart");
});
