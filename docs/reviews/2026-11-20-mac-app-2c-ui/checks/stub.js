// Stub window.anyscribeDesktop (bridge v2 at 2c-app 70e911f) for the click-through check.
// Injected before the page loads with window.__STUB_CFG set. Every call is recorded in
// window.__calls as [name, args]; results come from the config.
// The app's process memory is sessionStorage (it survives the app's reload of the page);
// the app's disk is localStorage. By default it behaves as the real bridge: removal restarts
// the engine and reloads the page, /api fails while the engine is not running, and so on.
// cfg.componentNoReload turns the removal's restart off for simplified component cases, which
// the checker labels "[component]".
(() => {
  const cfg = window.__STUB_CFG;
  if (!cfg) return; // browser mode: no bridge at all
  // calls survive a reload (removing the old launcher reloads the page), like the app's own state
  const calls = (window.__calls = JSON.parse(sessionStorage.getItem("__stub_calls") || "[]"));
  const clone = (v) => (v === undefined ? v : JSON.parse(JSON.stringify(v)));
  // results[name] may be a list: each call takes the next one, the last one repeats
  const take = (name, fallback) => {
    const r = cfg.results && cfg.results[name];
    if (r === undefined) return clone(fallback);
    if (!Array.isArray(r)) return clone(r);
    const i = used[name] || 0;
    used[name] = i + 1;
    sessionStorage.setItem("__stub_used", JSON.stringify(used));
    return clone(r[Math.min(i, r.length - 1)]);
  };
  const rec = (name, args) => {
    calls.push([name, JSON.parse(JSON.stringify(args))]);
    sessionStorage.setItem("__stub_calls", JSON.stringify(calls));
  };
  // results lists also survive a reload: each list's position is kept per name
  const used = JSON.parse(sessionStorage.getItem("__stub_used") || "{}");
  const wait = () => new Promise((res) => setTimeout(res, cfg.delay || 30));

  // The engine's state is the app's, so it survives the page's reloads.
  let engine = JSON.parse(sessionStorage.getItem("__stub_engine") || "null") || clone(cfg.engine);
  const saveEngine = () => sessionStorage.setItem("__stub_engine", JSON.stringify(engine));
  // app memory: survives the page's reloads
  const mem = (key, initial) => JSON.parse(sessionStorage.getItem(key) || "null") ?? clone(initial);
  const keep = (key, value) => sessionStorage.setItem(key, JSON.stringify(value));
  let terminal = mem("__stub_terminal", cfg.terminal);
  let settings = mem("__stub_settings", cfg.settings);
  let launcher = mem("__stub_launcher", cfg.launcher);
  const saveTerminal = () => keep("__stub_terminal", terminal);
  const saveSettings = () => keep("__stub_settings", settings);
  const engineListeners = new Set();
  let statusCalls = 0;
  const fileListeners = new Set();
  // files the app still holds (not yet handed to a callback, so not acknowledged), kept across reloads
  const heldFiles = JSON.parse(sessionStorage.getItem("__stub_held") || "[]");
  const saveHeld = () => sessionStorage.setItem("__stub_held", JSON.stringify(heldFiles));
  // first-launch answers: in the app's memory always, on its disk only when the save worked
  const disk = () => JSON.parse(localStorage.getItem("__stub_marks") || "{}");
  const memMarks = () => JSON.parse(sessionStorage.getItem("__stub_marks_mem") || "{}");

  // As the engine being down: the dashboard's requests to /api fail while it is not running. Every
  // /api request also carries the app's reload count, so a check can tell which page sent it.
  {
    const realFetch = window.fetch.bind(window);
    const pageNo = sessionStorage.getItem("__stub_reloads") || "0";
    window.fetch = (input, init) => {
      const url = typeof input === "string" ? input : input.url;
      const api = /\/api\//.test(new URL(url, location.href).pathname);
      if (api && cfg.engineDownApi !== false && engine.state !== "running") {
        return Promise.reject(new TypeError("Failed to fetch"));
      }
      if (!api) return realFetch(input, init);
      const headers = new Headers((init && init.headers) || (typeof input === "string" ? undefined : input.headers));
      headers.set("x-stub-page", pageNo);
      return realFetch(input, { ...init, headers });
    };
  }

  // a removal this page started earlier (its note), for the "older lastRemoval" check
  if (cfg.removingNote && !sessionStorage.getItem("__stub_noted")) {
    const at = Date.now();
    localStorage.setItem("anyscribe_launcher_removing", JSON.stringify({ at, before: null }));
    sessionStorage.setItem("__stub_noted_at", String(at));
    sessionStorage.setItem("__stub_noted", "1");
  }

  // As 2c-app main.js (engine 'status' handler): the status goes to the page, and on every return to
  // running the app loads the dashboard's / again (mainWin.loadURL(`${origin}/`)).
  window.__emit = (status) => {
    const was = engine.state;
    engine = { ...engine, ...status };
    saveEngine();
    engineListeners.forEach((cb) => cb(clone(engine)));
    if (engine.state === "running" && was !== "running") {
      sessionStorage.setItem("__stub_reloads", String(Number(sessionStorage.getItem("__stub_reloads") || 0) + 1));
      setTimeout(() => location.assign("/"), cfg.reloadDelay ?? 300); // the old page can act meanwhile
    }
  };
  // As the preload: a file is acknowledged once the page's callbacks returned, even if one threw;
  // with none subscribed the app keeps it. (The preload's ids never reach the page.)
  const deliver = (path) => fileListeners.forEach((cb) => {
    try { cb(path); } catch (e) { console.error(e); }
  });
  window.__openFile = (path) => {
    if (fileListeners.size) deliver(path);
    else {
      heldFiles.push(path);
      saveHeld();
    }
  };

  window.anyscribeDesktop = {
    version: cfg.version,
    platform: cfg.platform,
    getSettings: async () => { rec("getSettings", []); await wait(); return take("getSettings", settings); },
    setDockMode: async (mode) => { rec("setDockMode", [mode]); settings.dockMode = mode; saveSettings(); await wait(); },
    setStartAtLogin: async (on) => {
      rec("setStartAtLogin", [on]);
      settings.startAtLogin = cfg.loginNeedsApproval && on ? false : on;
      saveSettings();
      await wait();
    },
    engineStatus: async () => { rec("engineStatus", []); return clone(engine); },
    onEngineStatus: (cb) => {
      rec("onEngineStatus", []);
      engineListeners.add(cb);
      return () => engineListeners.delete(cb);
    },
    // As engine.restart(): refused at once, or "restarting", then "running" (the app reloads the page),
    // and the promise settles once the engine is ready.
    restartEngine: async () => {
      rec("restartEngine", []);
      await wait();
      const r = take("restartEngine", { ok: true });
      if (!r.ok) return r;
      window.__emit({ state: "restarting", stoppedRestarting: false }); // as engine.restart()
      await new Promise((res) => setTimeout(res, cfg.restartMs ?? 400)); // longer when a check screenshots the gap
      window.__emit({ state: "running", stoppedRestarting: false });
      return r;
    },
    openLogFolder: async () => { rec("openLogFolder", []); },
    revealInFinder: async (p) => { rec("revealInFinder", [p]); },
    pathForFile: (file) => { rec("pathForFile", [file.name]); return cfg.fileDir + "/" + file.name; },
    terminal: {
      status: async () => { rec("terminal.status", []); await wait(); terminal = take("terminal.status", terminal); saveTerminal(); return clone(terminal); },
      turnOn: async (opts) => { rec("terminal.turnOn", [opts]); await wait(); const r = take("terminal.turnOn", { ...terminal, ok: true, state: "on", command: "/Users/test/.local/bin/anyscribe", skill: terminal.claudeCode ? "installed" : "not-applicable", uses: { path: "/Users/test/.local/bin/anyscribe", version: terminal.appVersion, via: "app" }, occupant: null, reason: null }); if (r.ok !== false) { terminal = r; saveTerminal(); } return r; },
      turnOff: async (opts) => { rec("terminal.turnOff", opts === undefined ? [] : [opts]); await wait(); const r = take("terminal.turnOff", { ok: true }); if (r.ok) { terminal = { ...terminal, state: "off", command: null, skill: terminal.claudeCode ? "missing" : "not-applicable" }; saveTerminal(); } return r; },
      addToPath: async () => { rec("terminal.addToPath", []); await wait(); return take("terminal.addToPath", { ok: true, file: "/Users/test/.zprofile", line: 'export PATH="$HOME/.local/bin:$PATH"' }); },
      retrySkill: async () => { rec("terminal.retrySkill", []); await wait(); const r = take("terminal.retrySkill", { ...terminal, ok: true, skill: "installed" }); terminal = r; saveTerminal(); return r; },
    },
    oldLauncher: {
      status: async () => {
        rec("oldLauncher.status", []);
        statusCalls += 1; // per page: cfg.slowStatus {"<call number>": ms} makes that call's answer slow
        // the answer is what the stub knew when asked, delivered later (the real handler, main.js, reads lastRemoval after its pieces read; no check depends on the difference)
        const last = JSON.parse(sessionStorage.getItem("__stub_lastRemoval") || "null");
        const answer = { lastRemoval: cfg.lastRemoval || null, ...take("oldLauncher.status", launcher), ...(last ? { lastRemoval: last } : {}) };
        const slow = cfg.slowStatus || {}; // "<call>" on every page, or "<page>:<call>" on one page
        const page = sessionStorage.getItem("__stub_reloads") || "0";
        await new Promise((res) => setTimeout(res, slow[`${page}:${statusCalls}`] ?? slow[String(statusCalls)] ?? cfg.delay ?? 30));
        return answer;
      },
      remove: async () => {
        rec("oldLauncher.remove", []);
        await wait();
        // as engine.restart(): it first reads the job list (one HTTP read) before "restarting"
        if (cfg.removeCheckMs) await new Promise((res) => setTimeout(res, cfg.removeCheckMs));
        const r = take("oldLauncher.remove", { ok: true, pieces: { launcher: "removed", loginItem: "removed", menuBarIcon: "stopped" }, startAtLoginCarriedOver: true });
        // As removePausingEngine: a refusal (no pieces) answers at once and nothing is kept. Otherwise
        // the engine restarts around the removal, the result is kept (lastRemoval) before the engine
        // is back, and the return to running reloads the page. A removal that threw is kept too,
        // with pieces null (cfg.removalThrew).
        const refused = !r.ok && !r.pieces && !cfg.removalThrew;
        // a refusal can take one job check to arrive (a crash meanwhile makes it "stopped while checked")
        if (refused && cfg.refusalMs) await new Promise((res) => setTimeout(res, cfg.refusalMs));
        if (refused) return r;
        // what the removal changed, in the app: the pieces now gone, and Start at login carried over
        const applyResult = () => {
          if (r.pieces) {
            const p = {
              launcher: r.pieces.launcher === "removed" ? "absent" : "present",
              loginItem: r.pieces.loginItem === "removed" ? "absent" : "present",
              menuBarIcon: r.pieces.menuBarIcon === "stopped" ? "not running" : "running",
            };
            launcher = { installed: p.launcher === "present" || p.loginItem === "present" || p.menuBarIcon === "running", pieces: p };
            keep("__stub_launcher", launcher);
          }
          if (r.startAtLoginCarriedOver) {
            settings.startAtLogin = true;
            saveSettings();
          }
        };
        if (cfg.componentNoReload) {
          applyResult();
          sessionStorage.setItem("__stub_lastRemoval", JSON.stringify({ ...r, at: Date.now() })); // the app saves it either way
          return r;
        }
        window.__emit({ state: "restarting" });
        await new Promise((res) => setTimeout(res, 200));
        applyResult();
        sessionStorage.setItem("__stub_lastRemoval", JSON.stringify({ ...r, at: Date.now() }));
        // the engine did not start again: no reload, the result comes back with the engine stopped
        if (cfg.removalEngineStops) {
          window.__emit({ state: "stopped", stoppedRestarting: false, lastExit: { code: 1, signal: null, reason: null } });
          return r;
        }
        // As engine.restart(): the removal settles once the engine is ready, so after "running"; the
        // app's reload comes cfg.reloadDelay later, so the old page can act on the settled result.
        await new Promise((res) => setTimeout(res, cfg.restartMs ?? 250));
        window.__emit({ state: "running" });
        await new Promise((res) => setTimeout(res, 20));
        sessionStorage.setItem("__stub_remove_settled_engine", engine.state); // B3: checked by the checker
        return r;
      },
    },
    firstLaunch: {
      get: async () => { rec("firstLaunch.get", []); return { ok: true, ...cfg.firstLaunch, ...disk(), ...memMarks() }; },
      // As main.js: settings[key] = true in memory, then the save to disk, which can fail
      mark: async (key) => {
        rec("firstLaunch.mark", [key]);
        sessionStorage.setItem("__stub_marks_mem", JSON.stringify({ ...memMarks(), [key]: true }));
        if (cfg.markFails) return { ok: false, reason: "anyscribe couldn't save that this was asked: EACCES: permission denied" };
        localStorage.setItem("__stub_marks", JSON.stringify({ ...disk(), [key]: true }));
        return { ok: true };
      },
    },
    onOpenFile: (cb) => {
      rec("onOpenFile", []);
      fileListeners.add(cb);
      while (heldFiles.length) {
        const path = heldFiles.shift();
        saveHeld();
        try { cb(path); } catch (e) { console.error(e); }
      }
      return () => fileListeners.delete(cb);
    },
  };
})();
