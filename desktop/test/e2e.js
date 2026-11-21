// End-to-end run of the real app against the real engine, with nothing on screen:
// Electron runs with no display (--ozone-platform=headless), a throwaway HOME inside
// test/.tmp, and every process is stopped by the pid this script started or read.
//   ANYSCRIBE_DEV_PYTHON=/path/to/.venv/bin/python npm run e2e
// Not part of `npm test`: it needs a Python with anyscribe installed.
'use strict';

const { spawn } = require('node:child_process');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');

const APP = path.join(__dirname, '..');
const ELECTRON = require('electron'); // the binary's path when required from Node
const HOME = path.join(__dirname, '.tmp', `e2e-home-${process.pid}`);
const LOG = path.join(HOME, '.anyscribe', 'logs', 'app.log');
const DEBUG_PORT = 9333;
const INSPECT_PORT = 9334; // the app's main process, to press what a person would press (close, Quit)
const python = process.env.ANYSCRIBE_DEV_PYTHON;
if (!python) throw new Error('set ANYSCRIBE_DEV_PYTHON');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const alive = (pid) => {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
};
async function waitFor(fn, ms, what) {
  const end = Date.now() + ms;
  for (;;) {
    const v = await fn();
    if (v) return v;
    if (Date.now() > end) throw new Error(`timed out waiting for ${what}`);
    await sleep(100);
  }
}
const logText = () => (fs.existsSync(LOG) ? fs.readFileSync(LOG, 'utf8') : '');
const readyPids = () => [...logText().matchAll(/engine ready \(pid (\d+), port (\d+)\)/g)].map((m) => Number(m[1]));
async function health(port = 8470) {
  try {
    const r = await fetch(`http://127.0.0.1:${port}/api/health`, { signal: AbortSignal.timeout(1000) });
    return r.ok && (await r.json()).app === 'anyscribe';
  } catch {
    return false;
  }
}

// A stand-in xdg-open first on the app's PATH: "open in the browser" is recorded, never shown.
const BIN = path.join(HOME, 'bin');
const OPENED = path.join(HOME, 'opened.txt');
const opened = () => (fs.existsSync(OPENED) ? fs.readFileSync(OPENED, 'utf8').split('\n').filter(Boolean) : []);

const launched = [];
function launch(extra = [], enginePython = python) {
  const env = { HOME, PATH: `${BIN}:/usr/bin:/bin`, LANG: 'en_US.UTF-8', ANYSCRIBE_DEV_PYTHON: enginePython };
  const child = spawn(ELECTRON, [`--inspect=${INSPECT_PORT}`, APP, '--ozone-platform=headless', `--remote-debugging-port=${DEBUG_PORT}`, ...extra], {
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  launched.push(child);
  child.output = '';
  child.stdout.on('data', (d) => (child.output += d));
  child.stderr.on('data', (d) => (child.output += d));
  return child;
}

async function pages() {
  try {
    const r = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/list`);
    return (await r.json()).filter((p) => p.type === 'page');
  } catch {
    return null;
  }
}

// Runtime.evaluate in a page over the DevTools protocol (the renderer only, never the app's main process).
async function evaluate(page, expression) {
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => ((ws.onopen = res), (ws.onerror = rej)));
  const reply = new Promise((res) => (ws.onmessage = (m) => res(JSON.parse(m.data))));
  ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression, awaitPromise: true, returnByValue: true } }));
  const msg = await reply;
  ws.close();
  if (msg.result.exceptionDetails) throw new Error(JSON.stringify(msg.result.exceptionDetails));
  return msg.result.result.value;
}

// Runs `expression` in the app's main process, the way a menu click or the window's close button would.
async function inMain(expression) {
  const [target] = await (await fetch(`http://127.0.0.1:${INSPECT_PORT}/json/list`)).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => ((ws.onopen = res), (ws.onerror = rej)));
  const reply = new Promise((res) => (ws.onmessage = (m) => res(JSON.parse(m.data))));
  ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression, includeCommandLineAPI: true, returnByValue: true } }));
  const msg = await reply;
  ws.close();
  return msg.result.result.value;
}
const DASH_WINDOW = "require('electron').BrowserWindow.getAllWindows().find((w) => w.webContents.getURL().startsWith('http://127.0.0.1:'))";

const exitOf = (child) =>
  child.exitCode !== null || child.signalCode !== null
    ? Promise.resolve()
    : new Promise((r) => child.once('exit', r));

const results = [];
const step = (name, detail = '') => {
  results.push(`PASS ${name}${detail ? ` (${detail})` : ''}`);
  console.log(results.at(-1));
};

async function main() {
  fs.mkdirSync(BIN, { recursive: true });
  fs.writeFileSync(path.join(BIN, 'xdg-open'), `#!/bin/sh\necho "$1" >> '${OPENED}'\n`, { mode: 0o755 });
  // No menu bar icon here: on Linux a tray icon needs the desktop session (it would appear in the
  // owner's panel) or a display. "dock" mode is the app's own no-tray setting; the menu's content
  // is covered by the unit tests.
  const userData = path.join(HOME, '.config', 'anyscribe');
  fs.mkdirSync(userData, { recursive: true });
  fs.writeFileSync(path.join(userData, 'settings.json'), JSON.stringify({ dockMode: 'dock' }));
  for (const p of [8470, 8471, DEBUG_PORT]) assert.equal(await health(p), false, `port ${p} must be free`);

  // 1. Starts the engine and loads the dashboard.
  let app = launch();
  await waitFor(() => readyPids().length >= 1, 60_000, 'engine ready');
  const enginePid = readyPids()[0];
  assert.ok(alive(enginePid));
  const t0 = Date.now();
  const dash = await waitFor(async () => (await pages())?.find((p) => p.url === 'http://127.0.0.1:8470/'), 30_000, 'dashboard page');
  await waitFor(() => evaluate(dash, "document.readyState === 'complete' && document.getElementById('root')?.childElementCount > 0"), 30_000, 'dashboard rendered');
  step('engine starts and the dashboard loads', `engine pid ${enginePid}, page ${dash.url}, ${Date.now() - t0} ms after ready`);
  const bridge = await evaluate(dash, `(async () => ({ keys: Object.keys(window.anyscribeDesktop).sort(), status: await window.anyscribeDesktop.engineStatus(), settings: await window.anyscribeDesktop.getSettings(), version: window.anyscribeDesktop.version, node: typeof require }))()`);
  assert.deepEqual(bridge.keys, ['engineStatus', 'getSettings', 'onEngineStatus', 'openLogFolder', 'pathForFile', 'platform', 'restartEngine', 'revealInFinder', 'setDockMode', 'setStartAtLogin', 'version']);
  assert.equal(bridge.status.state, 'running');
  assert.equal(bridge.status.port, 8470);
  assert.deepEqual(bridge.settings, { dockMode: 'dock', startAtLogin: false });
  assert.equal(bridge.node, 'undefined');
  step('the bridge answers in the dashboard, no Node in the page', `version ${bridge.version}, status ${JSON.stringify(bridge.status)}`);

  // 2. Closing the window (its close button) keeps the engine up.
  assert.equal(await inMain(`${DASH_WINDOW}.isVisible()`), true, 'dashboard window shown');
  await inMain(`${DASH_WINDOW}.close()`);
  await sleep(1500);
  assert.equal(await inMain(`${DASH_WINDOW}?.isVisible()`), false, 'window hidden, not destroyed');
  assert.ok(alive(enginePid) && (await health()), 'engine still answering');
  assert.equal(app.exitCode, null, 'app still running');
  step('closing the window hides it; app and engine keep running');

  // 3. A second launch exits and leaves the first one in charge.
  const second = launch();
  await waitFor(() => second.exitCode !== null, 15_000, 'second instance to exit');
  assert.equal(readyPids().length, 1, 'no second engine');
  assert.ok(alive(enginePid));
  await waitFor(() => inMain(`${DASH_WINDOW}.isVisible()`), 5000, 'the hidden window to show again');
  step('opening the app again shows the hidden window (single instance)', `second launch exit code ${second.exitCode}`);

  // 4. The engine dies: restarted automatically, and the window reloads the dashboard.
  const page = (await pages()).find((p) => p.url === 'http://127.0.0.1:8470/');
  await evaluate(page, '(window.__beforeRestart = true)');
  process.kill(enginePid, 'SIGKILL'); // the pid the app logged
  await waitFor(() => readyPids().length >= 2, 60_000, 'the engine to be restarted');
  const restartedPid = readyPids()[1];
  await waitFor(async () => {
    const p = (await pages()).find((x) => x.url === 'http://127.0.0.1:8470/');
    return p && (await evaluate(p, "window.__beforeRestart === undefined && document.readyState === 'complete'").catch(() => false));
  }, 30_000, 'the dashboard to reload');
  assert.match(logText(), /engine stopped unexpectedly \(code null, signal SIGKILL\)\n.*restarting the engine/);
  step('a crashed engine is restarted and the dashboard reloads', `pid ${enginePid} killed, new pid ${restartedPid}`);

  // 5. Quit (what the menu's Quit anyscribe does) stops the engine; no jobs, so no question.
  await inMain("require('electron').app.quit()").catch(() => {});
  await waitFor(() => !alive(restartedPid), 20_000, 'engine to stop after quit');
  await exitOf(app);
  assert.match(logText(), new RegExp(`quitting: stopping the engine \\(pid ${restartedPid}\\)`));
  step('quitting the app stops the engine', `pid ${restartedPid} gone, app exit ${app.exitCode ?? app.signalCode}`);

  // 6. A --hidden launch (what a login launch should look like): no window, engine still starts.
  app = launch(['--hidden']);
  await waitFor(() => readyPids().length >= 3, 60_000, 'engine ready (--hidden launch)');
  await sleep(1000);
  const hiddenPages = await pages();
  assert.deepEqual(hiddenPages, [], 'no window created');
  const hiddenPid = readyPids()[2];
  step('a --hidden launch starts the engine with no window', `engine pid ${hiddenPid}`);

  // 7. Force-killed app: the engine follows (--watch-stdin). Cleanup in finally stops it if not.
  app.kill('SIGKILL');
  await exitOf(app);
  await waitFor(() => !alive(hiddenPid), 15_000, `engine pid ${hiddenPid} to follow the force-killed app`);
  step('a force-killed app takes its engine with it', `pid ${hiddenPid} gone`);

  // 8. Port taken: "couldn't start", and the program holding it is left alone.
  const holder = net.createServer((s) => s.on('error', () => {}).end('HTTP/1.1 200 OK\r\ncontent-length: 2\r\n\r\nno'));
  await new Promise((r) => holder.listen(8470, '127.0.0.1', r));
  const before = readyPids().length;
  app = launch();
  const start = await waitFor(async () => (await pages())?.find((p) => p.url.endsWith('/start.html')), 15_000, 'start window');
  const failed = await waitFor(() => evaluate(start, "!document.getElementById('failed')?.hidden && document.getElementById('message').textContent").catch(() => false), 15_000, 'failure state');
  assert.equal(failed, "Its engine couldn't start: another program is using port 8470. Your transcripts and settings are safe.");
  assert.equal(await evaluate(start, "document.querySelector('img').naturalWidth"), 256, 'start window icon loads');
  assert.equal(readyPids().length, before, 'no engine started');
  assert.ok(holder.listening, 'the holder is still listening');
  step('a taken port shows "couldn\'t start" and leaves the holder alone', failed);
  // Quit with no engine running (SIGTERM: the path logout and shutdown take).
  app.kill('SIGTERM');
  await Promise.race([exitOf(app), sleep(10_000)]);
  assert.notEqual(app.exitCode ?? app.signalCode, null, 'the app quits with its engine never started');
  step('quitting from "couldn\'t start" exits the app', `exit ${app.exitCode}`);
  holder.close();

  // 9. Links, frames and redirects (C3). The fake engine (test/fake-engine.js) serves a page and
  // a redirect out of 127.0.0.1, which the real engine has no route for.
  const fakePython = path.join(BIN, 'fake-python');
  fs.writeFileSync(fakePython, `#!/bin/sh\nexec '${process.execPath}' '${path.join(__dirname, 'fake-engine.js')}' "$@"\n`, { mode: 0o755 });
  app = launch([], fakePython);
  const fake = await waitFor(async () => (await pages())?.find((p) => p.url === 'http://127.0.0.1:8470/'), 30_000, 'fake dashboard');
  await waitFor(() => evaluate(fake, "document.readyState === 'complete'").catch(() => false), 10_000, 'fake page loaded');
  const frameAt = (src) =>
    evaluate(fake, `new Promise((done) => { const f = document.createElement('iframe'); f.src = ${JSON.stringify(src)}; document.body.append(f); setTimeout(() => { try { done(f.contentWindow.location.href); } catch (e) { done('cross-origin: ' + e.name); } }, 1500); })`);
  assert.equal(await frameAt('http://example.invalid/framed'), 'about:blank', 'an outside iframe never loads');
  assert.equal(await frameAt('/redirect-out'), 'about:blank', 'a frame redirected out never loads');
  assert.deepEqual(opened(), [], 'frames are blocked, not opened in the browser');
  await evaluate(fake, "location.href = '/redirect-out'").catch(() => {});
  await waitFor(() => opened().includes('http://example.invalid/away'), 5000, 'the redirect to open outside');
  assert.ok((await pages()).some((p) => p.url === 'http://127.0.0.1:8470/'), 'the window stayed on the app');
  const pagesBefore = (await pages()).length;
  await evaluate(fake, "window.open('http://example.invalid/popup'), true");
  await waitFor(() => opened().includes('http://example.invalid/popup'), 5000, 'the outside popup to open outside');
  assert.equal((await pages()).length, pagesBefore, 'no window for an outside popup');
  await evaluate(fake, "window.open('/'), true");
  await waitFor(async () => (await pages()).length === pagesBefore + 1, 5000, 'a popup inside the app');
  step('outside frames and redirects never load in the app; outside pages and popups open in the browser', `opened: ${opened().join(', ')}`);
  app.kill('SIGTERM');
  await exitOf(app);

  // 10. Stop and Quit quits straight away (G7): no job read, no per-job cancel. The fake engine
  // answers /api/jobs once with active jobs, then never again. The question's buttons are pressed
  // by replacing dialog.showMessageBox in the main process with one that answers "Stop and Quit".
  const jobsPython = path.join(BIN, 'fake-python-jobs');
  const activeJobs = JSON.stringify([
    { job_id: 'j1', url: 'https://example.invalid/a', status: 'running', stage: 'transcribe', title: 'A' },
    { job_id: 'j2', url: 'https://example.invalid/b', status: 'pending', stage: null, title: null },
  ]);
  fs.writeFileSync(
    jobsPython,
    `#!/bin/sh\nFAKE_JOBS='${activeJobs}' FAKE_JOBS_ANSWERS=1 exec '${process.execPath}' '${path.join(__dirname, 'fake-engine.js')}' "$@"\n`,
    { mode: 0o755 }
  );
  const readyBefore = readyPids().length;
  app = launch([], jobsPython);
  await waitFor(() => readyPids().length > readyBefore, 30_000, 'the fake engine to be ready');
  const fakePid = readyPids().at(-1);
  await sleep(5000); // one poll answered (two active jobs), later polls hang
  // The stand-in records the question on stdout, so a quit that asked nothing cannot pass.
  await inMain(
    "require('electron').dialog.showMessageBox = async (...a) => { const box = a.at(-1); process.stdout.write('ASKED ' + box.buttons[1] + '\\n'); return { response: 1 }; }, true"
  ); // "Stop and Quit"
  const quitAt = Date.now();
  await inMain("require('electron').app.quit()").catch(() => {});
  await Promise.race([exitOf(app), sleep(5000)]);
  const quitMs = Date.now() - quitAt;
  assert.notEqual(app.exitCode ?? app.signalCode, null, 'the app quit');
  assert.ok(quitMs < 1000, `Stop and Quit took ${quitMs} ms`);
  await waitFor(() => !alive(fakePid), 3000, `engine pid ${fakePid} to stop`);
  assert.match(app.output, /ASKED Stop and Quit/, 'the quit question was asked and answered Stop and Quit');
  assert.ok(!/fake got POST/.test(logText()), 'no request was sent to the engine');
  step('Stop and Quit quits at once; the engine stops; no job read or cancel was sent', `${quitMs} ms, pid ${fakePid} gone`);
}

main()
  .then(() => {
    console.log(`\n${results.join('\n')}\n\nlog: ${LOG}`);
  })
  .catch((err) => {
    console.error('FAIL', err);
    process.exitCode = 1;
  })
  .finally(() => {
    // Leave nothing behind: only pids this run started or logged.
    for (const c of launched) if (c.exitCode === null && c.signalCode === null) c.kill('SIGKILL');
    for (const pid of readyPids()) if (alive(pid)) process.kill(pid, 'SIGTERM');
  });
