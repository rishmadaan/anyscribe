// run.js: helpers that opt in are ended by killHelpers() (what quitting does), group and all;
// others are left alone.
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { runCapture, killHelpers } = require('../src/run');

const ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'anyscribe-run-test-'));
test.after(() => fs.rmSync(ROOT, { recursive: true, force: true }));

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
  while (!fn()) {
    if (Date.now() > end) throw new Error(`timed out waiting for ${what}`);
    await new Promise((r) => setTimeout(r, 25));
  }
}
const readPids = (file) => (fs.existsSync(file) ? fs.readFileSync(file, 'utf8').trim().split(/\s+/).filter(Boolean).map(Number) : []);

test('guard: killHelpers ends an opted-in helper and its grandchild; a helper that did not opt in keeps running (B2)', async () => {
  const opted = path.join(ROOT, 'opted');
  const other = path.join(ROOT, 'other');
  const env = { PATH: '/usr/bin:/bin' };
  // sh records its own pid and its grandchild's, then waits.
  const optedRun = runCapture('/bin/sh', ['-c', `sleep 30 & echo $$ $! > '${opted}'; wait`], { env, timeoutMs: 20_000, helper: true });
  const otherRun = runCapture('/bin/sh', ['-c', `sleep 30 & echo $$ $! > '${other}'; wait`], { env, timeoutMs: 20_000 });
  await waitFor(() => readPids(opted).length === 2 && readPids(other).length === 2, 5000, 'both helpers');
  const [helper, grandchild] = readPids(opted);
  const [otherHelper, otherGrandchild] = readPids(other);
  killHelpers();
  const r = await optedRun;
  assert.equal(r.signal, 'SIGKILL', 'the helper was killed');
  await waitFor(() => !alive(grandchild), 5000, 'the grandchild to go');
  assert.equal(alive(helper), false);
  assert.equal(alive(grandchild), false, 'its whole group went');
  assert.equal(alive(otherHelper) && alive(otherGrandchild), true, 'the other helper is untouched');
  process.kill(-otherHelper, 'SIGKILL'); // the group this test started
  await otherRun;
});
