// Runs a short helper command (a login shell, `anyscribe --version`, `skill install`, `desktop
// uninstall`) and captures its output. Node only. The helper leads its own process group, and
// whatever is left of that group is killed when it finishes or times out, so a login shell's rc
// files can never leave a process behind or hold the answer open.
'use strict';

const childProcess = require('node:child_process');

// The process groups of helpers that opted in (helper: true; only the old launcher's uninstall
// does), so quitting can end them: the uninstall must not outlive the app that paused its engine.
const helpers = new Set();

// Ends every opted-in helper's group at once (SIGKILL), without waiting: quit stays instant.
function killHelpers() {
  for (const pid of helpers) {
    try {
      process.kill(-pid, 'SIGKILL');
    } catch {
      // already gone
    }
  }
  helpers.clear();
}

// Resolves {out, err, code, signal, timedOut, error}; never rejects. `until`: resolve as soon as
// stdout contains this text (a login shell's end marker), without waiting for the shell to exit.
function runCapture(cmd, args, { env, cwd, timeoutMs, until = null, helper = false }) {
  return new Promise((resolve) => {
    const result = { out: '', err: '', code: null, signal: null, timedOut: false, error: null };
    let child;
    let timer;
    let done = false;
    const finish = (extra = {}) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      if (child?.pid) helpers.delete(child.pid);
      if (child?.pid) {
        try {
          process.kill(-child.pid, 'SIGKILL');
        } catch {
          // the group is already gone
        }
      }
      resolve(Object.assign(result, extra));
    };
    try {
      child = childProcess.spawn(cmd, args, { env, cwd, stdio: ['ignore', 'pipe', 'pipe'], detached: true });
    } catch (error) {
      return finish({ error });
    }
    if (helper && child.pid) helpers.add(child.pid);
    timer = setTimeout(() => finish({ timedOut: true }), timeoutMs);
    child.stdout.on('data', (d) => {
      result.out += d;
      if (until && result.out.includes(until)) finish({ code: 0 });
    });
    child.stderr.on('data', (d) => (result.err += d));
    child.on('error', (error) => finish({ error }));
    child.on('close', (code, signal) => finish({ code, signal }));
  });
}

// The last line that says something: a rich error box's borders (box-drawing characters) and
// blank lines are skipped.
const lastLine = (text) =>
  String(text || '')
    .split('\n')
    .map((l) => l.replace(/[\u2500-\u257f]/g, '').trim())
    .filter((l) => /[\p{L}\p{N}]/u.test(l))
    .pop() || null;

module.exports = { runCapture, killHelpers, lastLine };
