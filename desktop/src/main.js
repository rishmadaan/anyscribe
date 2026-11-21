// The anyscribe Mac app: starts the engine, shows the dashboard, lives in the menu bar.
'use strict';

const { app, BrowserWindow, Menu, Tray, clipboard, dialog, ipcMain, nativeImage, nativeTheme, shell } = require('electron');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const logic = require('./logic');
const { Engine, AppLog } = require('./engine');

const GUIDE_URL = 'https://github.com/rishmadaan/anyscribe/blob/main/docs/user/troubleshooting.md';
const ASSETS = path.join(__dirname, '..', 'assets');
const START_URL = pathToFileURL(path.join(__dirname, 'start.html')).href;
const DOCK_MODES = ['menubar', 'both', 'dock'];
const isMac = process.platform === 'darwin';

if (!app.requestSingleInstanceLock()) {
  app.quit(); // a second launch: the first instance focuses its window
} else {
  run();
}

function run() {
  const home = os.homedir();
  const logFile = path.join(home, '.anyscribe', 'logs', 'app.log');
  const log = new AppLog(logFile);
  let python = null;
  let pythonError = null;
  try {
    python = logic.resolvePython({
      packaged: app.isPackaged,
      resourcesPath: process.resourcesPath,
      env: process.env,
      cwd: process.cwd(),
    });
  } catch (err) {
    pythonError = err.message;
  }
  const engine = new Engine({
    python,
    pythonError,
    packaged: app.isPackaged,
    home,
    log,
    env: logic.buildEnv({
      home,
      packaged: app.isPackaged,
      resourcesPath: process.resourcesPath,
      execPath: process.execPath,
      tmpdir: os.tmpdir(),
    }),
  });

  let settings = { dockMode: 'menubar' };
  let mainWin = null;
  let startWin = null;
  let tray = null;
  let latestJobs = []; // the last job list read; kept when a read fails
  let jobsKnown = true; // false while the last read failed
  let failedReads = 0; // job reads that failed in a row
  let hiddenSince = null; // when the dashboard window was last closed; null while it is shown
  let finished = new Map(); // jobs that finished while it was hidden, by id
  let quitWhenDone = false;
  let quitting = false; // a quit question or engine stop is under way
  let allowQuit = false;
  let lastMenuKey = '';

  const engineOrigin = () => `http://127.0.0.1:${engine.port}`;
  const visible = (w) => w && !w.isDestroyed() && w.isVisible();

  // ---- settings (userData/settings.json) ----

  const settingsFile = () => path.join(app.getPath('userData'), 'settings.json');
  function loadSettings() {
    try {
      const s = JSON.parse(fs.readFileSync(settingsFile(), 'utf8'));
      return { dockMode: DOCK_MODES.includes(s.dockMode) ? s.dockMode : 'menubar' };
    } catch {
      return { dockMode: 'menubar' };
    }
  }
  function saveSettings() {
    try {
      fs.mkdirSync(path.dirname(settingsFile()), { recursive: true });
      fs.writeFileSync(settingsFile(), `${JSON.stringify(settings, null, 2)}\n`);
    } catch (err) {
      log.shell(`couldn't save settings: ${err.message}`); // the choice still applies until quit
    }
  }
  // The system's Login Items are the source of truth (he can turn it off in System Settings,
  // or it can wait for approval there); nothing is stored for it here.
  function startsAtLogin() {
    const s = app.getLoginItemSettings();
    return s.status ? s.status === 'enabled' : s.openAtLogin === true;
  }

  function setStartAtLogin(on) {
    app.setLoginItemSettings({ openAtLogin: on === true });
    refreshMenu();
  }
  function setDockMode(mode) {
    if (!DOCK_MODES.includes(mode)) throw new Error(`dockMode must be one of ${DOCK_MODES.join(', ')}`);
    settings.dockMode = mode;
    saveSettings();
    applyDockMode();
  }

  // ---- windows ----

  const secure = (preload) => ({ preload: path.join(__dirname, preload), contextIsolation: true, nodeIntegration: false, sandbox: true });

  function hideOnClose(win) {
    win.on('close', (e) => {
      if (allowQuit) return;
      e.preventDefault(); // closing only hides; the app keeps running
      win.hide();
    });
    win.on('show', onVisibility);
    win.on('hide', onVisibility);
    // A page's own window.close() (the dashboard's Shutdown button) destroys it without 'close'.
    win.on('closed', () => {
      if (mainWin === win) {
        mainWin = null;
        hiddenSince ??= Date.now(); // still "closed" for the Finished-while-closed menu
      }
      if (startWin === win) startWin = null;
      onVisibility();
    });
  }

  function onVisibility() {
    if (visible(mainWin)) hiddenSince = null;
    else if (hiddenSince == null && mainWin) hiddenSince = Date.now();
    finished = logic.rememberFinished(finished, latestJobs, hiddenSince);
    updateDock();
    refreshMenu();
  }

  function ensureStartWindow() {
    if (startWin && !startWin.isDestroyed()) return startWin;
    startWin = new BrowserWindow({
      width: 560,
      height: 360,
      resizable: false,
      show: false,
      title: 'anyscribe',
      backgroundColor: '#0B0A0F',
      ...(isMac ? { titleBarStyle: 'hiddenInset' } : {}),
      webPreferences: secure('start-preload.js'),
    });
    hideOnClose(startWin);
    startWin.loadURL(START_URL);
    return startWin;
  }

  function ensureMainWindow() {
    if (mainWin && !mainWin.isDestroyed()) return mainWin;
    mainWin = new BrowserWindow({
      width: 1200,
      height: 800,
      minWidth: 760,
      minHeight: 520,
      show: false,
      title: 'anyscribe',
      backgroundColor: '#0B0A0F',
      // Default title bar until the dashboard has a drag area (slice 2c), then hiddenInset.
      webPreferences: { ...secure('preload.js'), additionalArguments: [`--anyscribe-version=${app.getVersion()}`] },
    });
    hideOnClose(mainWin);
    mainWin.loadURL(`${engineOrigin()}/`);
    return mainWin;
  }

  // Open anyscribe: the dashboard when the engine runs, else the start window with its state.
  function showUI() {
    if (engine.state === 'running') {
      const win = ensureMainWindow();
      const reveal = () => {
        win.show();
        win.focus();
        if (visible(startWin)) startWin.hide(); // after, so the Dock icon does not blink
      };
      if (win.webContents.isLoading()) win.webContents.once('did-finish-load', reveal);
      else reveal();
    } else {
      const win = ensureStartWindow();
      win.show();
      win.focus();
    }
  }

  function startState() {
    const f = engine.failure;
    if (engine.state !== 'stopped' || !f) return { phase: 'starting' };
    return { phase: 'failed', message: logic.failureMessage(f), lines: f.lines };
  }

  // ---- menu bar, Dock ----

  function trayImage(icon) {
    if (icon === 'plain') return nativeImage.createFromPath(path.join(ASSETS, 'trayTemplate.png'));
    const theme = nativeTheme.shouldUseDarkColors ? 'dark' : 'light'; // coloured dot: not a template
    return nativeImage.createFromPath(path.join(ASSETS, `tray-${icon}-${theme}.png`));
  }

  // macOS 14 (Darwin 23) and later draw a section header; older systems get a greyed item.
  const headerItem = (label) =>
    isMac && Number(os.release().split('.')[0]) >= 23 ? { type: 'header', label } : { label, enabled: false };

  function menuTemplate(model, forDock) {
    const action = {
      restartEngine: { label: 'Restart engine', click: () => engine.restart() },
      open: { label: 'Open anyscribe', accelerator: 'CmdOrCtrl+O', click: showUI },
      startAtLogin: { label: 'Start at login', type: 'checkbox', checked: startsAtLogin(), click: (item) => setStartAtLogin(item.checked) },
      quit: { label: 'Quit anyscribe', accelerator: 'CmdOrCtrl+Q', click: () => app.quit() },
      dontQuit: { label: "Don't quit", click: () => ((quitWhenDone = false), refreshMenu()) },
      stopAndQuit: { label: 'Stop and quit now', click: () => finalQuit() },
    };
    const rows = [...model.rows];
    return logic
      .menuLayout(model)
      .filter((id) => !(forDock && (id === 'open' || id === 'quit'))) // the Dock has its own
      .map((id) => {
        if (id === 'header') return headerItem(model.header);
        if (id === 'separator') return { type: 'separator' };
        if (id === 'row') {
          const row = rows.shift();
          return { label: row.stage ? `${row.label} · ${row.stage}` : row.label, enabled: false };
        }
        return action[id];
      })
      .filter((item, i, all) => !(item.type === 'separator' && (i === all.length - 1 || all[i - 1].type === 'separator')));
  }

  function refreshMenu() {
    const model = logic.menuModel({
      engineState: engine.state,
      stoppedRestarting: engine.stoppedRestarting,
      jobs: latestJobs,
      finished: [...finished.values()],
      quitWhenDone,
      failedReads,
    });
    const key = JSON.stringify([model, settings, startsAtLogin(), nativeTheme.shouldUseDarkColors, Boolean(tray)]);
    if (key === lastMenuKey) return;
    lastMenuKey = key;
    if (tray) {
      tray.setImage(trayImage(model.icon));
      tray.setContextMenu(Menu.buildFromTemplate(menuTemplate(model, false)));
    } else if (app.dock) {
      app.dock.setMenu(Menu.buildFromTemplate(menuTemplate(model, true)));
    }
  }

  function updateDock() {
    if (!app.dock) return;
    const shown = visible(mainWin) || visible(startWin);
    if (settings.dockMode === 'menubar' && !shown) app.dock.hide();
    else app.dock.show();
  }

  function applyDockMode() {
    const wantTray = settings.dockMode !== 'dock';
    if (wantTray && !tray) {
      tray = new Tray(trayImage('plain'));
      tray.setToolTip('anyscribe');
    } else if (!wantTray && tray) {
      tray.destroy();
      tray = null;
    }
    if (wantTray && app.dock) app.dock.setMenu(Menu.buildFromTemplate([]));
    lastMenuKey = '';
    updateDock();
    refreshMenu();
  }

  // ---- quitting (mockup section 7) ----

  function finalQuit() {
    quitting = true;
    allowQuit = true;
    // Never inside the before-quit that started this: Electron would reset its quitting
    // state when that handler returns, close every window and keep running.
    setImmediate(() => app.quit());
  }

  async function askQuit({ box, choices }) {
    quitting = true;
    try {
      app.focus({ steal: true }); // the question must not open behind the front app
      const { response } = visible(mainWin) ? await dialog.showMessageBox(mainWin, box) : await dialog.showMessageBox(box);
      const choice = choices[response] ?? 'cancel';
      // Stop and Quit: straight to the normal quit; the engine's stop (stdin and SIGTERM to its
      // group, in will-quit) ends every job. No job read, no per-job cancels to wait on.
      if (choice === 'stopAndQuit') return finalQuit();
      if (choice === 'whenDone') {
        quitWhenDone = true;
        for (const w of [mainWin, startWin]) if (visible(w)) w.hide();
        refreshMenu();
      }
    } finally {
      if (!allowQuit) quitting = false;
    }
  }

  // Every quit path (Cmd Q, the menus, logout, shutdown) arrives here first. Idle: the quit goes
  // ahead untouched, so a logout or shutdown is not interrupted; the engine stops in will-quit.
  app.on('before-quit', (e) => {
    if (allowQuit) return;
    const decision = logic.quitDecision({ running: engine.state === 'running', known: jobsKnown, jobs: latestJobs });
    if (!decision) {
      allowQuit = true;
      return;
    }
    e.preventDefault();
    if (!quitting) setImmediate(() => askQuit(decision));
  });
  app.on('will-quit', () => engine.stopForQuit());
  app.on('window-all-closed', () => {}); // keep running in the menu bar

  // ---- engine events and the job poll ----

  engine.on('status', (status) => {
    if (startWin) startWin.webContents.send('start:state', startState());
    mainWin?.webContents.send('engine:status', status);
    if (status.state === 'running') {
      if (mainWin && !mainWin.isDestroyed()) mainWin.loadURL(`${engineOrigin()}/`); // after a restart
      if (visible(startWin)) showUI(); // someone is waiting for it
    }
    lastMenuKey = '';
    refreshMenu();
  });

  async function poll() {
    const jobs = await engine.jobs();
    jobsKnown = jobs !== null;
    failedReads = jobsKnown ? 0 : failedReads + 1;
    if (jobsKnown) latestJobs = jobs;
    finished = logic.rememberFinished(finished, latestJobs, hiddenSince);
    if (quitWhenDone && !quitting && logic.quitWhenDoneReady({ known: jobsKnown, jobs: latestJobs })) return finalQuit();
    refreshMenu();
  }

  // ---- links: anything that leaves 127.0.0.1 opens in the default browser ----

  const ours = (url) => url.startsWith(`${engineOrigin()}/`) || url === START_URL;
  const where = (url, isMainFrame) => logic.navigation(url, [`${engineOrigin()}/`], START_URL, isMainFrame);
  // Every page, popup and frame: navigations (main frame and subframes) and server redirects.
  app.on('web-contents-created', (_e, contents) => {
    contents.setWindowOpenHandler(({ url }) => {
      const decision = where(url, true);
      if (decision === 'allow') return { action: 'allow' };
      if (decision === 'outside') shell.openExternal(url);
      return { action: 'deny' };
    });
    const guard = (e) => {
      const decision = where(e.url, e.isMainFrame);
      if (decision === 'allow') return;
      e.preventDefault();
      if (decision === 'outside') shell.openExternal(e.url);
    };
    contents.on('will-frame-navigate', guard);
    contents.on('will-redirect', guard);
  });

  // ---- the bridges ----

  function handle(channel, fn) {
    ipcMain.handle(channel, (e, ...args) => {
      if (!ours(e.senderFrame?.url || '')) throw new Error('not allowed from this page');
      return fn(...args);
    });
  }
  handle('settings:get', () => ({ ...settings, startAtLogin: startsAtLogin() }));
  handle('settings:dockMode', (mode) => setDockMode(mode));
  handle('settings:startAtLogin', (on) => setStartAtLogin(on));
  handle('engine:status', () => engine.status());
  handle('engine:restart', () => engine.restart());
  handle('open:logFolder', () => shell.openPath(path.dirname(logFile)));
  handle('open:reveal', (p) => {
    if (typeof p !== 'string' || !path.isAbsolute(p)) throw new Error('revealInFinder needs an absolute path');
    shell.showItemInFolder(p);
  });
  handle('start:state', () => startState());
  handle('start:retry', () => engine.state === 'stopped' && engine.start());
  handle('start:copy', () => clipboard.writeText(log.tail(40).join('\n')));
  handle('start:guide', () => shell.openExternal(GUIDE_URL));

  // ---- launch ----

  app.on('second-instance', showUI);
  app.on('activate', showUI); // Dock icon clicked, or the app opened again while running
  nativeTheme.on('updated', refreshMenu);

  app.whenReady().then(() => {
    settings = loadSettings();
    const atLogin = process.argv.includes('--hidden') || (isMac && app.getLoginItemSettings().wasOpenedAtLogin);
    if (atLogin) hiddenSince = Date.now(); // menu bar only, no window
    else showUI();
    applyDockMode();
    engine.start();
    setInterval(poll, 2000);
  });
}
