// Pure decisions for the Mac app shell: no Electron, no I/O. Tested in test/logic.test.js.
'use strict';

const path = require('node:path');

const DEFAULT_PORT = 8470;

// One function picks the port. The app keeps the port it last ran on (saved), so the
// dashboard's per-port storage stays put, unless the old launcher now records it; a first
// choice is 8470 or the next port up that the old launcher does not record (avoid).
function choosePort({ saved = null, avoid = [] } = {}) {
  if (Number.isInteger(saved) && !avoid.includes(saved)) return saved;
  let port = DEFAULT_PORT;
  while (avoid.includes(port)) port += 1;
  return port;
}

// Packaged: the Python inside the app. Dev: ANYSCRIBE_DEV_PYTHON, made absolute against the
// directory the app was started from (the engine itself runs in HOME).
function resolvePython({ packaged, resourcesPath, env, cwd }) {
  if (packaged) return path.join(resourcesPath, 'python', 'bin', 'python3');
  if (!env.ANYSCRIBE_DEV_PYTHON) {
    throw new Error(
      "ANYSCRIBE_DEV_PYTHON isn't set. Point it at a Python with anyscribe installed, " +
        "for example the repo's .venv/bin/python."
    );
  }
  const dev = env.ANYSCRIBE_DEV_PYTHON;
  return dev.includes(path.sep) ? path.resolve(cwd, dev) : dev; // a bare name is looked up on PATH
}

const SYSTEM_PATH = ['/usr/bin', '/bin', '/usr/sbin', '/sbin'];
const DEV_EXTRA_PATH = ['/usr/local/bin', '/opt/homebrew/bin']; // a system ffmpeg in dev

// Built from scratch, never inherited: an app opened from Finder lacks Terminal's PATH,
// and the packaged engine must only see the tools shipped inside the app.
function buildEnv({ home, packaged, resourcesPath, execPath, tmpdir }) {
  const pathDirs = packaged
    ? [path.join(resourcesPath, 'bin'), ...SYSTEM_PATH]
    : [...SYSTEM_PATH, ...DEV_EXTRA_PATH];
  const env = {
    HOME: home,
    PATH: pathDirs.join(':'),
    ANYSCRIBE_APP: '1',
    PYTHONUSERBASE: path.join(home, '.anyscribe', 'runtime'),
    PIP_USER: '1',
    LANG: 'en_US.UTF-8',
    PYTHONUNBUFFERED: '1',
    TMPDIR: tmpdir,
  };
  if (packaged) env.ANYSCRIBE_ELECTRON = execPath; // yt-dlp's JavaScript runtime
  return env;
}

// The add-ons folder Python only honours when it already exists.
function userSitePackages(home) {
  return path.join(home, '.anyscribe', 'runtime', 'lib', 'python3.13', 'site-packages');
}

// --watch-stdin: the engine stops when the app's end of its stdin closes (slice 2a).
function engineArgs(port) {
  return ['-m', 'anyscribe', 'ui', '--port', String(port), '--no-open', '--watch-stdin'];
}

// ---- jobs → menu ----

const isActive = (job) => job.status === 'pending' || job.status === 'running';

function stageWord(job) {
  if (job.status === 'pending') return 'Waiting';
  switch (job.stage) {
    case 'transcribe':
      return 'Transcribing';
    case 'write':
    case 'index':
    case 'cached':
      return 'Saving';
    default:
      return 'Downloading'; // a running job starts with its download
  }
}

function truncate(text, max) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

// Title once known, else the link without its scheme, shortened like the mockup.
function jobName(job) {
  if (job.title) return truncate(job.title, 42);
  const url = String(job.url || '').replace(/^[a-z]+:\/\//i, '').replace(/^www\./, '');
  return truncate(url, 25);
}

// Seconds (today's engine) or an ISO string; null when unknown.
function toMillis(value) {
  if (value == null) return null;
  if (typeof value === 'number') return value < 1e12 ? value * 1000 : value;
  const ms = Date.parse(value);
  return Number.isNaN(ms) ? null : ms;
}

function countWords(running, waiting) {
  const parts = [];
  if (running) parts.push(`${running} running`);
  if (waiting) parts.push(`${waiting} waiting`);
  return parts.join(', ');
}

// Jobs that finished (saved or failed) while the window was hidden, kept by id until it is
// shown again, so the engine's 50-row list cannot drop them from the menu. hiddenSince: ms
// since the window was closed (or the app launched hidden), null while it is shown.
function rememberFinished(memory, jobs, hiddenSince) {
  if (hiddenSince == null) return new Map();
  for (const j of jobs) {
    const done = j.status === 'completed' || j.status === 'failed';
    if (done && (toMillis(j.completed_at) ?? 0) >= hiddenSince) memory.set(j.job_id, j);
  }
  return memory;
}

const ROW_CAP = 5; // finished rows, and waiting rows

const NOT_ANSWERING_AFTER = 3; // failed job reads in a row

// What the menu (tray or Dock) says. `actions` are ids main.js turns into menu items.
// finished: rememberFinished's jobs. failedReads: job reads that failed in a row; from three on,
// the header says the engine is not answering (the rows are the last list it gave).
function menuModel(input) {
  const model = menuState(input);
  if (input.engineState === 'running' && (input.failedReads ?? 0) >= NOT_ANSWERING_AFTER) {
    // Idle: "Not answering" replaces "Ready" (they contradict); otherwise it is added.
    model.header = model.header === 'anyscribe · Ready' ? 'anyscribe · Not answering' : `${model.header} · not answering`;
  }
  return model;
}

function menuState({ engineState, stoppedRestarting, jobs = [], finished = [], quitWhenDone = false }) {
  const active = jobs.filter(isActive);
  const running = active.filter((j) => j.status === 'running').length;
  const waiting = active.length - running;
  // Running rows always (at most two run at once); waiting rows capped like finished ones.
  const row = (j) => ({ label: jobName(j), stage: stageWord(j) });
  const queued = active.filter((j) => j.status !== 'running');
  const activeRows = [...active.filter((j) => j.status === 'running').map(row), ...queued.slice(0, ROW_CAP).map(row)];
  if (queued.length > ROW_CAP) activeRows.push({ label: `and ${queued.length - ROW_CAP} more waiting`, stage: null });

  if (quitWhenDone) {
    return {
      icon: 'working',
      header: 'Quitting when these finish',
      rows: activeRows,
      actions: ['dontQuit', 'stopAndQuit'],
    };
  }
  if (engineState === 'stopped' && stoppedRestarting) {
    return {
      icon: 'alert',
      header: "Engine stopped · couldn't restart",
      rows: [],
      actions: ['restartEngine', 'open', 'startAtLogin', 'quit'],
    };
  }
  if (engineState === 'stopped') {
    return { icon: 'alert', header: "anyscribe · Couldn't start", rows: [], actions: ['open', 'startAtLogin', 'quit'] };
  }
  if (engineState === 'starting' || engineState === 'restarting') {
    const header = engineState === 'starting' ? 'anyscribe · Starting' : 'anyscribe · Restarting the engine';
    return { icon: 'plain', header, rows: [], actions: ['open', 'startAtLogin', 'quit'] };
  }

  // Failed first (the row he needs), then newest; 5 rows, then one "and N more" line. The header
  // still counts them all.
  const failedFirst = (j) => (j.status === 'failed' ? 1 : 0);
  const newest = [...finished].sort(
    (a, b) => failedFirst(b) - failedFirst(a) || (toMillis(b.completed_at) ?? 0) - (toMillis(a.completed_at) ?? 0)
  );
  const finishedRows = newest.slice(0, ROW_CAP).map((j) => ({
    label: jobName(j),
    stage: j.status === 'completed' ? 'Saved' : 'Failed',
  }));
  if (newest.length > ROW_CAP) finishedRows.push({ label: `and ${newest.length - ROW_CAP} more finished`, stage: null });
  const failed = finished.some((j) => j.status === 'failed');
  const actions = ['open', 'startAtLogin', 'quit'];

  if (active.length) {
    return {
      icon: failed ? 'alert' : 'working',
      header: `Transcribing · ${countWords(running, waiting)}`,
      rows: [...activeRows, ...finishedRows],
      actions,
    };
  }
  if (finished.length) {
    const saved = finished.filter((j) => j.status === 'completed').length;
    const parts = [];
    if (saved) parts.push(`${saved} saved`);
    if (failed) parts.push(`${finished.length - saved} failed`);
    return { icon: failed ? 'alert' : 'plain', header: `anyscribe · ${parts.join(', ')}`, rows: finishedRows, actions };
  }
  return { icon: 'plain', header: 'anyscribe · Ready', rows: [], actions };
}

// The menu's lines in order, as mockup section 6 draws them: the header, the job rows, then the
// actions; a separator before "Open anyscribe" only when job rows are shown, none before
// "Restart engine" or "Stop and quit now", one before every other action.
function menuLayout(model) {
  const layout = ['header', ...model.rows.map(() => 'row')];
  for (const id of model.actions) {
    const separate = id === 'open' ? model.rows.length > 0 : id !== 'restartEngine' && id !== 'stopAndQuit';
    if (separate) layout.push('separator');
    layout.push(id);
  }
  return layout;
}

// ---- quitting ----

function isAre(n) {
  return n === 1 ? 'is' : 'are';
}

// null when nothing is pending or running: quit without asking.
function quitQuestion(jobs) {
  const active = jobs.filter(isActive);
  if (!active.length) return null;
  const running = active.filter((j) => j.status === 'running').length;
  const waiting = active.length - running;
  const parts = [];
  if (running) parts.push(`${running} ${isAre(running)} running`);
  if (waiting) parts.push(`${waiting} ${isAre(waiting)} waiting`);
  const counts = parts.join(' and ');
  return {
    type: 'question',
    message: 'Transcriptions are still running',
    detail: `${counts[0].toUpperCase()}${counts.slice(1)}. Quit when they finish, or stop them now? To finish a stopped one later, transcribe it again.`,
    buttons: ['Quit When Done', 'Stop and Quit', 'Cancel'],
    defaultId: 0,
    cancelId: 2,
  };
}

// The job list is unknown: the approved three buttons, Quit When Done first (it waits for a
// known list with nothing left).
const UNKNOWN_QUIT = {
  type: 'question',
  message: "anyscribe couldn't check which transcriptions are running",
  detail: 'Quit when they finish, or stop them now? To finish a stopped one later, transcribe it again.',
  buttons: ['Quit When Done', 'Stop and Quit', 'Cancel'],
  defaultId: 0,
  cancelId: 2,
};

// Every quit path (Cmd Q, the menus, logout, shutdown), decided at once from the last poll so
// an idle logout is never held up. null: quit now. Otherwise the question to ask and what each
// button means. An unknown job list is never read as "no jobs".
function quitDecision({ running, known, jobs }) {
  if (!running) return null;
  if (!known) return { box: UNKNOWN_QUIT, choices: ['whenDone', 'stopAndQuit', 'cancel'] };
  const box = quitQuestion(jobs);
  return box && { box, choices: ['whenDone', 'stopAndQuit', 'cancel'] };
}

// Quit When Done quits only on a known list with nothing pending or running.
function quitWhenDoneReady({ known, jobs }) {
  return known && !jobs.some(isActive);
}

// The engine's job list if it has the expected shape, else null (unknown).
function validJobs(body) {
  const ok =
    Array.isArray(body) &&
    body.every((j) => j !== null && typeof j === 'object' && typeof j.job_id === 'string' && typeof j.status === 'string');
  return ok ? body : null;
}

const RESTART_REFUSED = 'Wait for transcriptions to finish before restarting the engine.';
const RESTART_UNKNOWN = "anyscribe couldn't check for running transcriptions; try again in a moment";

// Restart engine is unavailable while any job is pending or running, or while that is unknown (null).
function restartRefusal(jobs) {
  if (jobs === null) return RESTART_UNKNOWN;
  return jobs.some(isActive) ? RESTART_REFUSED : null;
}

// ---- links ----

// Where a navigation may go: 'allow' inside the app (the engine's origin, the start page, and a
// frame's blank document); else 'outside' for a top-level http(s) page, which opens in the
// browser; else 'block' (another origin in a frame, other schemes).
function navigation(url, prefixes, startUrl, isMainFrame) {
  if (url === startUrl || prefixes.some((p) => url.startsWith(p))) return 'allow';
  if (!isMainFrame && (url === 'about:blank' || url === 'about:srcdoc')) return 'allow';
  return isMainFrame && /^https?:\/\//i.test(url) ? 'outside' : 'block';
}

// ---- the start window's "couldn't start" sentence (mockup section 2) ----

const SAFE = 'Your transcripts and settings are safe.';

// removal: the old launcher's removal that ran just before this start, if any (its result is
// said too, so a removal is never silent behind "couldn't start").
function failureMessage(failure, removal = null) {
  const said = removal ? ` The old launcher's removal ran first: ${removal.ok ? 'it was removed.' : removal.reason}` : '';
  return startFailure(failure) + said;
}

function startFailure(failure) {
  switch (failure.kind) {
    case 'port':
      return `Its engine couldn't start: ${failure.reason}. ${SAFE}`;
    case 'timeout':
      return `Its engine didn't answer within a minute. ${SAFE}`;
    case 'crashes':
      return `Its engine stopped 3 times in a minute, so anyscribe stopped restarting it. ${SAFE}`;
    case 'python':
      return `Its engine couldn't be found. ${failure.reason} ${SAFE}`;
    case 'log':
      return `${failure.reason}. ${SAFE}`;
    default:
      return `Its engine stopped before it was ready. ${SAFE}`;
  }
}

// ---- the app's settings (userData/settings.json) ----

const DOCK_MODES = ['menubar', 'both', 'dock'];
const FIRST_LAUNCH_KEYS = ['oldLauncherAsked', 'terminalAsked']; // each first-launch question, asked once

// Whatever the file holds (or nothing): a known Dock mode, and true only for a question asked.
function parseSettings(saved) {
  const s = saved && typeof saved === 'object' ? saved : {};
  return {
    dockMode: DOCK_MODES.includes(s.dockMode) ? s.dockMode : 'menubar',
    oldLauncherAsked: s.oldLauncherAsked === true,
    terminalAsked: s.terminalAsked === true,
    port: Number.isInteger(s.port) && s.port > 1023 && s.port < 65536 ? s.port : null, // the port the app last ran on
  };
}

// ---- files opened with the app (the Dock icon, a second launch) ----

// A second launch's command line: absolute paths to files, never argv[0] (the app's own
// binary), a flag, or the app's folder in dev.
function openedFiles(argv, isFile) {
  return argv.slice(1).filter((a) => !a.startsWith('-') && path.isAbsolute(a) && isFile(a));
}

// Each file is held, with an id, until the dashboard acknowledges it (its callback ran): sending
// is not receiving. A subscriber gets every unacknowledged file in order; an unsubscribe or a
// reload before the ack leaves it held for the next one. An ack for an unknown id does nothing,
// so an acknowledged file is never sent again.
class OpenFiles {
  constructor() {
    this.held = []; // [{id, file}]
    this.nextId = 1;
    this.deliver = null;
  }
  add(file) {
    const item = { id: this.nextId++, file };
    this.held.push(item);
    this.deliver?.(item);
  }
  subscribe(deliver) {
    this.deliver = deliver;
    for (const item of this.held) deliver(item);
  }
  unsubscribe() {
    this.deliver = null;
  }
  ack(id) {
    this.held = this.held.filter((item) => item.id !== id);
  }
}

// ---- crashes ----

// Three unexpected exits within 60 s: stop retrying.
class CrashWindow {
  constructor(limit = 3, windowMs = 60_000) {
    this.limit = limit;
    this.windowMs = windowMs;
    this.exits = [];
  }
  // Returns true when the engine should not be restarted again.
  record(now) {
    this.exits = this.exits.filter((t) => now - t < this.windowMs);
    this.exits.push(now);
    return this.exits.length >= this.limit;
  }
  reset() {
    this.exits = [];
  }
}

module.exports = {
  DEFAULT_PORT,
  choosePort,
  resolvePython,
  buildEnv,
  userSitePackages,
  engineArgs,
  isActive,
  stageWord,
  jobName,
  menuModel,
  rememberFinished,
  menuLayout,
  quitQuestion,
  quitDecision,
  quitWhenDoneReady,
  UNKNOWN_QUIT,
  validJobs,
  restartRefusal,
  RESTART_REFUSED,
  RESTART_UNKNOWN,
  failureMessage,
  navigation,
  CrashWindow,
  DOCK_MODES,
  FIRST_LAUNCH_KEYS,
  parseSettings,
  openedFiles,
  OpenFiles,
};
