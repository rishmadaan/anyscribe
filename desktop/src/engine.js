// Starts, watches and stops the anyscribe engine (`python -m anyscribe ui`).
// Node only (no Electron), so the tests drive it with a fake engine or with seams.
'use strict';

const childProcess = require('node:child_process');
const EventEmitter = require('node:events');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const logic = require('./logic');

const LOG_MAX = 5 * 1024 * 1024;
const LOG_KEEP = 1024 * 1024;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Over `max` at launch: keep the last `keep` bytes, starting at a whole line.
function trimLog(file, max = LOG_MAX, keep = LOG_KEEP) {
  let size;
  try {
    size = fs.statSync(file).size;
  } catch {
    return;
  }
  if (size <= max) return;
  const buf = Buffer.alloc(keep);
  const fd = fs.openSync(file, 'r');
  try {
    fs.readSync(fd, buf, 0, keep, size - keep);
  } finally {
    fs.closeSync(fd);
  }
  const nl = buf.indexOf(10);
  fs.writeFileSync(file, nl >= 0 ? buf.subarray(nl + 1) : buf);
}

// ~/.anyscribe/logs/app.log: the engine's output plus one [app] line per start, stop, crash, restart.
// Never throws. `probe()` (before every launch) says whether the file can be appended to now;
// a failed write keeps the in-memory tail (Copy details) and the next good write clears it.
class AppLog {
  constructor(file) {
    this.file = file;
    this.recent = '';
    this.error = null;
    try {
      fs.mkdirSync(path.dirname(file), { recursive: true });
      trimLog(file);
    } catch (err) {
      this.error = err.message;
    }
  }
  probe() {
    try {
      fs.mkdirSync(path.dirname(this.file), { recursive: true });
      fs.appendFileSync(this.file, '');
      this.error = null;
    } catch (err) {
      this.error = err.message;
    }
    return this.error;
  }
  write(text) {
    this.recent = (this.recent + text).slice(-32_768);
    try {
      fs.appendFileSync(this.file, text);
      this.error = null;
    } catch (err) {
      this.error = err.message;
    }
  }
  shell(message) {
    this.write(`${new Date().toISOString()} [app] ${message}\n`);
  }
  tail(n = 40) {
    return this.recent.split('\n').filter(Boolean).slice(-n);
  }
}

// Taken = something answers on it (the engine's own test) or we cannot bind it.
function portTaken(port, host = '127.0.0.1') {
  return new Promise((resolve) => {
    const sock = net.connect({ port, host });
    sock.once('connect', () => {
      sock.destroy();
      resolve(true);
    });
    sock.once('error', () => {
      const srv = net.createServer();
      srv.once('error', () => resolve(true));
      srv.listen({ port, host, exclusive: true }, () => srv.close(() => resolve(false)));
    });
  });
}

function readManifestPort(home) {
  try {
    return JSON.parse(fs.readFileSync(path.join(home, '.anyscribe', 'desktop.json'), 'utf8')).port;
  } catch {
    return null; // no desktop mode installed (or an unreadable manifest)
  }
}

async function pickPort(home) {
  const port = logic.choosePort(readManifestPort(home));
  return { port, taken: await portTaken(port) };
}

// Signal a process group (the engine's pid, negated) so its helpers (pip, yt-dlp, ffmpeg) go
// with it; if the group cannot be signalled for another reason, the pid alone. "No such
// process" means it is already gone.
function killGroup(pid, signal) {
  try {
    process.kill(-pid, signal);
  } catch (err) {
    if (err.code === 'ESRCH') return;
    try {
      process.kill(pid, signal);
    } catch {
      // already gone
    }
  }
}

// GET /api/health: the parsed body, or null when nothing answers with JSON.
async function health(port) {
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/health`, { signal: AbortSignal.timeout(1000) });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

// GET /api/jobs, validated; null when the list cannot be known (timeout, error status, bad
// JSON, wrong shape): a slow engine may still be transcribing.
async function jobs(port) {
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/jobs`, { signal: AbortSignal.timeout(2000) });
    return res.ok ? logic.validJobs(await res.json()) : null;
  } catch {
    return null;
  }
}

const lastLine = (text) => text.split('\n').map((l) => l.trim()).filter(Boolean).pop() || null;

// The supervisor decides from the child process, not from remembered facts. `this.run` is the
// one current launch, set when a start or restart is accepted and cleared only by that child's
// exit (or a failure before spawn). Every late continuation passes one gate:
// `run === this.run && !run.cancelled`.
class Engine extends EventEmitter {
  // python: the interpreter; prefixArgs: what goes before `ui ...` (tests swap in a fake engine).
  // spawn, health, jobs, killGroup: seams for the tests, defaulting to the real ones.
  constructor({
    python,
    prefixArgs = ['-m', 'anyscribe'],
    home,
    env,
    log,
    readyTimeoutMs = 60_000,
    stopWaitMs = 10_000,
    pythonError = null,
    packaged = false,
    spawn = childProcess.spawn,
    health: healthSeam = health,
    jobs: jobsSeam = jobs,
    killGroup: killSeam = killGroup,
  }) {
    super();
    Object.assign(this, { python, prefixArgs, home, env, log, readyTimeoutMs, stopWaitMs, pythonError, packaged });
    Object.assign(this, { spawn, health: healthSeam, readJobs: jobsSeam, killGroup: killSeam });
    this.state = 'stopped';
    this.port = null;
    this.lastExit = null;
    this.stoppedRestarting = false;
    this.failure = null; // {kind: 'exited'|'port'|'timeout'|'crashes'|'python'|'log', reason, lines} for the start window
    this.run = null;
    this.restartPending = false;
    this.quitting = false; // set at quit: never spawn again
    this.crashes = new logic.CrashWindow();
  }

  status() {
    const { state, port, lastExit, stoppedRestarting } = this;
    return { state, port, lastExit, stoppedRestarting };
  }

  _set(state) {
    this.state = state;
    this.emit('status', this.status());
  }

  _current(run) {
    return run === this.run && !run.cancelled;
  }

  // User-initiated start: launch, Try again. Clears the crash count.
  start() {
    if (this.run || this.quitting) return Promise.resolve(false);
    this.crashes.reset();
    this.stoppedRestarting = false;
    return this._launch('starting', false);
  }

  // Resolves true once this run is ready, false when it ends first.
  _launch(state, auto) {
    let settle;
    const done = new Promise((resolve) => (settle = resolve));
    let exited;
    const exitedPromise = new Promise((resolve) => (exited = resolve));
    const run = { child: null, cancelled: false, restartRequested: false, ready: false, failure: null, auto, stdout: '', stderr: '', settle, exited, exitedPromise, next: null };
    this.run = run;
    this.failure = null;
    if (this.state !== state) this._set(state);
    this._start(run).catch((err) => this._failBeforeSpawn(run, 'exited', { reason: err.message }));
    return done;
  }

  async _start(run) {
    if (this.pythonError) return this._failBeforeSpawn(run, 'python', { reason: this.pythonError });
    const logError = this.log.probe(); // every launch, so Try again sees a repaired log
    if (logError) return this._failBeforeSpawn(run, 'log', { reason: `Can't write the log file: ${logError}` });
    const { port, taken } = await pickPort(this.home);
    if (!this._current(run)) return;
    this.port = port;
    // Never attach to, or stop, whatever already holds the port.
    if (taken) return this._failBeforeSpawn(run, 'port', { reason: `another program is using port ${port}` });
    let child;
    try {
      // The packaged Python's add-ons folder; a dev venv ignores user site-packages.
      if (this.packaged) fs.mkdirSync(logic.userSitePackages(this.home), { recursive: true });
      const args = [...this.prefixArgs, ...logic.engineArgs(port).slice(2)];
      // detached: the engine leads its own process group from birth (not unref'd: the app still
      // holds it and its stdin), so signalling the group also reaches its helpers.
      child = this.spawn(this.python, args, { env: this.env, cwd: this.home, stdio: 'pipe', detached: true });
    } catch (err) {
      return this._failBeforeSpawn(run, 'exited', { reason: err.message, lines: [`engine couldn't run: ${err.message}`] });
    }
    run.child = child;
    run.port = port;
    run.startedAt = Date.now();
    child.stdin.on('error', () => {}); // EPIPE once the engine is gone
    child.stdout.on('data', (d) => {
      this.log.write(d.toString());
      run.stdout = (run.stdout + d).slice(-8192);
    });
    child.stderr.on('data', (d) => {
      this.log.write(d.toString());
      run.stderr = (run.stderr + d).slice(-8192);
    });
    child.on('error', (error) => this._onExit(run, { code: null, signal: null, error }));
    child.on('exit', (code, signal) => this._onExit(run, { code, signal }));
    this.log.shell(`engine started (pid ${child.pid}, port ${port})`);
    this._waitReady(run);
  }

  async _waitReady(run) {
    const deadline = Date.now() + this.readyTimeoutMs;
    const pid = run.child.pid;
    for (;;) {
      if (!this._current(run)) return;
      const body = await this.health(run.port);
      if (!this._current(run)) return; // the child exited (or a stop came) while we asked: drop the answer
      if (body?.app === 'anyscribe') {
        if (body.pid === pid) {
          run.ready = true;
          this.log.shell(`engine ready (pid ${pid}, port ${run.port})`);
          this.lastExit = null;
          this._set('running');
          run.settle(true);
          return;
        }
        // anyscribe answered, but not our child: another program holds the port. Send it nothing.
        run.failure = { kind: 'port', reason: `another program is using port ${run.port}` };
        this.killGroup(pid, 'SIGKILL');
        return;
      }
      if (Date.now() > deadline) {
        run.failure = { kind: 'timeout', reason: null };
        this.killGroup(pid, 'SIGKILL');
        return;
      }
      await sleep(100);
    }
  }

  _failBeforeSpawn(run, kind, { reason = null, lines = [] } = {}) {
    if (this.run !== run) return;
    this.run = null;
    this._stopped(kind, { reason, lines });
    run.settle(false);
    run.exited();
  }

  _stopped(kind, { code = null, signal = null, reason = null, lines = [] }) {
    this.lastExit = { code, signal, reason };
    this.failure = { kind, reason, lines };
    this.log.shell(`engine not started: ${kind}${reason ? ` (${reason})` : ''}`);
    this._set('stopped');
  }

  // The one exit handler: every end of a spawned run comes here once, and decides what next.
  _onExit(run, { code, signal, error }) {
    if (run.done) return;
    run.done = true;
    clearTimeout(run.killTimer);
    if (this.run === run) this.run = null; // first, so a late health or jobs answer is dropped
    const pid = run.child.pid;
    // Whatever the dead engine left in its group goes with it, once (every exit: a helper may
    // have ignored the SIGTERM that a stop sent).
    this.killGroup(pid, 'SIGKILL');
    const reason = error ? error.message : lastLine(run.stderr);
    if (run.failure) {
      this._stopped(run.failure.kind, { code, signal, reason: run.failure.reason });
    } else if (run.cancelled) {
      this.log.shell(`engine stopped (pid ${pid})`);
      if (run.restartRequested && !this.quitting) {
        run.next = this._launch('restarting', false);
      } else {
        this.lastExit = null;
        this._set('stopped');
      }
    } else if (run.ready || run.auto) {
      this._crashed({ code, signal, reason });
    } else {
      const secs = ((Date.now() - run.startedAt) / 1000).toFixed(1);
      const head = error ? `engine couldn't run: ${error.message}` : `engine exited with ${signal ? `signal ${signal}` : `code ${code}`} after ${secs} s`;
      const lines = [head, ...run.stderr.split('\n').filter((l) => l.trim()).slice(-8), `log: ${this._tilde(this.log.file)}`];
      this._stopped('exited', { code, signal, reason, lines });
    }
    run.settle(false);
    run.exited();
  }

  // An exit nobody asked for: after ready, or an automatic restart that died early.
  _crashed({ code, signal, reason }) {
    this.lastExit = { code, signal, reason };
    this.log.shell(`engine stopped unexpectedly (code ${code}, signal ${signal})`);
    if (this.crashes.record(Date.now())) {
      this.stoppedRestarting = true;
      this.failure = {
        kind: 'crashes',
        reason,
        lines: [`engine exited with ${signal ? `signal ${signal}` : `code ${code}`}`, `log: ${this._tilde(this.log.file)}`],
      };
      this.log.shell('engine stopped 3 times in a minute; not restarting it');
      this._set('stopped');
      return;
    }
    if (this.quitting) return this._set('stopped');
    this.log.shell('restarting the engine');
    this._launch('restarting', true);
  }

  // The one stop: stdin closed, SIGTERM to the group, SIGKILL to the group if no exit comes in
  // time. No HTTP request: whoever answers on the port later may not be ours. Resolves on exit.
  stop() {
    // An explicit stop also revokes a restart's pending relaunch (not in _cancel: restart() sets
    // the flag and then cancels through it).
    if (this.run) this.run.restartRequested = false;
    return this._cancel(this.run, 'stopping the engine');
  }

  // At quit: the same stop, without waiting (a logout will not wait), and never spawn again.
  stopForQuit() {
    this.quitting = true;
    this._cancel(this.run, 'quitting: stopping the engine');
  }

  _cancel(run, words) {
    if (!run) {
      if (this.state !== 'stopped') this._set('stopped');
      return Promise.resolve();
    }
    run.cancelled = true;
    if (!run.child) {
      // Not spawned yet: the late port check sees it is no longer current and spawns nothing.
      this.run = null;
      this.lastExit = null;
      this._set('stopped');
      run.settle(false);
      run.exited();
      return run.exitedPromise;
    }
    if (!run.terminating) {
      run.terminating = true;
      const pid = run.child.pid;
      this.log.shell(`${words} (pid ${pid})`);
      run.child.stdin.end();
      this.killGroup(pid, 'SIGTERM');
      run.killTimer = setTimeout(() => {
        this.log.shell(`engine still running after ${this.stopWaitMs / 1000} s; killing pid ${pid}`);
        this.killGroup(pid, 'SIGKILL');
      }, this.stopWaitMs);
    }
    return run.exitedPromise;
  }

  // Refused while any job is pending or running, or while that cannot be known, and while
  // another restart is pending (not queued).
  async restart() {
    if (this.restartPending) return { ok: false, reason: 'A restart is already under way.' };
    if (this.state === 'starting' || this.state === 'restarting') {
      return { ok: false, reason: 'The engine is already starting.' };
    }
    if (this.quitting) return { ok: false, reason: 'anyscribe is quitting.' };
    this.restartPending = true;
    try {
      const run = this.run;
      const list = run ? await this.jobs() : [];
      if (run !== this.run || run?.cancelled || this.quitting) {
        return { ok: false, reason: 'The engine was stopped while the restart was being checked.' };
      }
      const refusal = logic.restartRefusal(list);
      if (refusal) return { ok: false, reason: refusal };
      this.crashes.reset();
      this.stoppedRestarting = false;
      this.log.shell('restarting the engine (asked for)');
      this._set('restarting');
      let ready;
      if (run) {
        run.restartRequested = true;
        await this._cancel(run, 'stopping the engine');
        ready = await (run.next ?? false);
      } else {
        ready = await this._launch('restarting', false);
      }
      return ready ? { ok: true, reason: null } : { ok: false, reason: this.lastExit?.reason ?? "The engine didn't start." };
    } finally {
      this.restartPending = false;
    }
  }

  // [] when no engine is running (nothing can be transcribing); else the validated list, or null.
  async jobs() {
    if (this.state !== 'running' || !this.run) return [];
    return this.readJobs(this.port);
  }


  _tilde(p) {
    return p.startsWith(this.home) ? `~${p.slice(this.home.length)}` : p;
  }
}

module.exports = { Engine, AppLog, trimLog, portTaken, pickPort, readManifestPort, killGroup, health, jobs };
