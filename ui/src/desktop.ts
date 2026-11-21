import { useEffect, useState } from "react";

/** The Mac app's bridge (window.anyscribeDesktop, contract v2). Present only
 * inside the app; in a browser `desktop` is null and every Mac screen stays
 * hidden. The one place the dashboard reads the bridge. */

export type DockMode = "menubar" | "both" | "dock";

/** `reason` may come with ok: true too (bridge v2 amendment): then it is information, not an error. */
export type Result = { ok: boolean; reason?: string | null };

export type EngineStatus = {
  state: "starting" | "running" | "restarting" | "stopped";
  port: number | null;
  lastExit: { code: number | null; signal: string | null; reason: string | null } | null;
  stoppedRestarting: boolean;
};

export type TerminalStatus = Result & {
  state: "off" | "on" | "other-copy" | "path-missing";
  command: string | null;
  uses: { path: string; version: string | null; via: "uv" | "pipx" | "pip" | "app" | "unknown" } | null;
  /** What sits at ~/.local/bin/anyscribe when it is not ours (amendment); Switch is offered only then. */
  occupant: { path: string; version: string | null; via: string } | null;
  appVersion: string;
  claudeCode: boolean;
  skill: "installed" | "missing" | "not-applicable";
};

export type TurnOffResult = Partial<TerminalStatus> &
  Result & { needsChoice?: "keep-current-or-restore" };

export type LauncherStatus = {
  installed: boolean;
  /** The most recent removal, kept by the app across the reload it causes (amendment 2). */
  lastRemoval?: (LauncherRemoval & { at: number | string }) | null;
  pieces: {
    launcher: "present" | "absent";
    loginItem: "present" | "absent";
    menuBarIcon: "running" | "not running";
  };
};

/** ok: false without pieces is a refusal (amendment 2: transcriptions running or waiting, the job
 * list unknown, or a restart pending, worded as Restart engine's); nothing changed. */
export type LauncherRemoval = Result & {
  pieces?: null | {
    launcher: "removed" | "still there";
    loginItem: "removed" | "still there";
    menuBarIcon: "stopped" | "still running";
  };
  startAtLoginCarriedOver: boolean;
};

export type FirstLaunch = { oldLauncherAsked: boolean; terminalAsked: boolean };

export interface Bridge {
  version: string;
  platform: string;
  getSettings(): Promise<{ dockMode: DockMode; startAtLogin: boolean }>;
  setDockMode(mode: DockMode): Promise<unknown>;
  setStartAtLogin(on: boolean): Promise<unknown>;
  engineStatus(): Promise<EngineStatus>;
  onEngineStatus(cb: (s: EngineStatus) => void): () => void;
  restartEngine(): Promise<Result>;
  openLogFolder(): Promise<unknown>;
  revealInFinder(path: string): Promise<unknown>;
  pathForFile(file: File): string;
  terminal: {
    status(): Promise<TerminalStatus>;
    turnOn(opts: { replace: boolean }): Promise<TerminalStatus>;
    /** `choice` answers a needsChoice conflict (bridge v2 amendment). */
    turnOff(opts?: { choice: "keep-current" | "restore" }): Promise<TurnOffResult>;
    /** Refused (ok: false) for bash when a new ~/.bash_profile would hide ~/.profile or
     * ~/.bash_login; `line` is then the exact line to add by hand. */
    addToPath(): Promise<Result & { file?: string; line?: string }>;
    retrySkill(): Promise<TerminalStatus>;
  };
  oldLauncher: {
    status(): Promise<LauncherStatus>;
    remove(): Promise<LauncherRemoval>;
  };
  firstLaunch: {
    get(): Promise<FirstLaunch>;
    /** {ok: false, reason} when the app couldn't save it (it still holds it until it quits). */
    mark(key: keyof FirstLaunch): Promise<Result | undefined>;
  };
  onOpenFile(cb: (path: string) => void): () => void;
}

export const desktop: Bridge | null =
  (window as unknown as { anyscribeDesktop?: Bridge }).anyscribeDesktop ?? null;

export const isMac = desktop?.platform === "darwin";

// A doomed page (H1, B1): the app reloads the dashboard on every return to running (2c-app main.js),
// so a page that has seen the engine leave running will be replaced. Set by the first status read
// and by any status event that is not running; never reset. Exactly two readers: the queue's start
// gate and the startup recovery claim. The first page after launch is loaded from a running engine.
let doomed = false;
let engineNow: EngineStatus["state"] | null = null;
if (desktop) {
  const seen = (s: EngineStatus) => {
    engineNow = s.state;
    if (s.state !== "running") doomed = true;
  };
  desktop.engineStatus().then(seen).catch(() => undefined);
  desktop.onEngineStatus(seen);
}
export const isDoomed = () => doomed;
/** The engine's state as this page last saw it (for decisions made in async callbacks). */
export const engineRunningNow = () => engineNow === "running";

export const GUIDE_URL =
  "https://github.com/rishmadaan/anyscribe/blob/main/docs/user/troubleshooting.md";

/** "the engine exited with code 1" / "was stopped by SIGKILL", for the trouble banner. */
export function exitWords(e: EngineStatus["lastExit"]): string {
  const how = e?.signal
    ? `The engine was stopped by ${e.signal}`
    : e?.code != null
      ? `The engine exited with code ${e.code}`
      : "The engine stopped";
  return e?.reason ? `${how}: ${e.reason}` : `${how}; the reason wasn't reported`;
}

/** Page state that must outlive the app's reload to / after every engine restart (2c-app main.js
 * loadURL). A restart keeps the port, so the origin and its sessionStorage survive the reload. */
export const session = {
  get<T>(key: string): T | null {
    try {
      const v = sessionStorage.getItem(key);
      return v ? (JSON.parse(v) as T) : null;
    } catch {
      return null;
    }
  },
  set(key: string, value: unknown) {
    try {
      sessionStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* storage off: this page's memory only */
    }
  },
  del(key: string) {
    try {
      sessionStorage.removeItem(key);
    } catch {
      /* storage off */
    }
  },
};

/** The engine stopped by itself while this page was open: {job, at}. Read after the reload. */
export const OUTAGE = "anyscribe_outage";
// "This restart is mine": true only while this page's own Restart engine or removal call is in
// flight. The app reloads the page only once the engine runs again, so a new page never needs it.
let ownCalls = 0;
export function restartIsMine(): boolean {
  return ownCalls > 0;
}
async function own<T>(call: () => Promise<T>): Promise<T> {
  ownCalls += 1;
  try {
    return await call();
  } finally {
    ownCalls -= 1;
  }
}

/** Restart engine, as this page's own restart (no outage, his words in the banner). */
export const restartEngine = (): Promise<Result> => own(() => desktop!.restartEngine());

/** A first-launch answer the app couldn't save: shown, so the question coming back is explained. */
export const MARK_PROBLEM = "anyscribe_mark_problem";
export const MARK_PROBLEM_EVENT = "anyscribe-mark-problem";
export type MarkProblem = { keys: ("oldLauncherAsked" | "terminalAsked")[]; reason: string };

/** Record a first-launch question as asked. The person's choice goes ahead either way (C6). */
export async function markAsked(key: "oldLauncherAsked" | "terminalAsked") {
  let r: Result | undefined;
  try {
    r = await desktop!.firstLaunch.mark(key);
  } catch (e) {
    r = { ok: false, reason: e instanceof Error ? e.message : String(e) };
  }
  if (r && r.ok === false) {
    // which questions, so the card can name them (G5)
    const prev = session.get<MarkProblem>(MARK_PROBLEM);
    const keys = [...new Set([...(prev?.keys ?? []), key])];
    session.set(MARK_PROBLEM, { keys, reason: r.reason || "anyscribe couldn't save your answer." } satisfies MarkProblem);
    window.dispatchEvent(new Event(MARK_PROBLEM_EVENT));
  }
}

/** Plain-words count of running transcriptions; null when the list can't be read. */
export async function runningJobs(): Promise<number | null> {
  try {
    const res = await fetch("/api/jobs");
    if (!res.ok) return null;
    const jobs: { status: string }[] = await res.json();
    return jobs.filter((j) => j.status === "pending" || j.status === "running").length;
  } catch {
    return null;
  }
}

/** The engine's state, live from the app; null outside the app or before the first read. */
export function useEngineStatus(): EngineStatus | null {
  const [status, setStatus] = useState<EngineStatus | null>(null);
  useEffect(() => {
    if (!desktop) return;
    let live = true;
    desktop.engineStatus().then((s) => live && setStatus(s)).catch(() => undefined);
    const off = desktop.onEngineStatus((s) => setStatus(s));
    return () => {
      live = false;
      off();
    };
  }, []);
  return status;
}

export const VIA: Record<string, string> = { uv: "with uv", pipx: "with pipx", pip: "with pip", app: "by another anyscribe app" };

/** The other copy Terminal runs: "anyscribe 0.19.0" and "with uv" (undefined when unknown). */
export function otherCopyWords(s: TerminalStatus) {
  const via = s.uses ? VIA[s.uses.via] : undefined;
  return { name: `anyscribe${s.uses?.version ? ` ${s.uses.version}` : ""}`, via };
}

/** "Another anyscribe 0.19.0 is already at ~/.local/bin/anyscribe, installed with uv." (F5) */
export function occupantWords(s: TerminalStatus): string {
  const o = s.occupant!;
  const via = VIA[o.via];
  return `Another anyscribe${o.version ? ` ${o.version}` : ""} is already at ~/.local/bin/anyscribe${via ? `, installed ${via}` : ""}.`;
}

/** Only an "app" copy is this app's anyscribe (amendment): never claim it otherwise. The readiness
 * gate (C5): "ready in Terminal" only when the login shell was asked and found this app's command. */
export function runsOurs(s: TerminalStatus | null): boolean {
  return s?.uses?.via === "app";
}

// Removing the old launcher restarts the engine around it (amendment 2), and the app reloads this
// page when the engine runs again. The page notes when it started a removal and what was there
// before ({at, before} in localStorage). The note is resolved in one place, against the app's own
// saved lastRemoval, and only while the engine reads running: a lastRemoval at or after the note
// means the removal ran; anything else means nothing ran (a refusal) and the note goes. The shape
// of a result never decides it: a removal that threw is also {ok: false, pieces: null}, and kept.
const REMOVING = "anyscribe_launcher_removing";
export type Pieces = LauncherStatus["pieces"];
type RemovalNote = { at: number; before: Pieces | null };
/** A removal's result with what was there before it; afterReload: claimed by a reloaded page. */
export type Removal = { result: LauncherRemoval; before: Pieces | null; afterReload: boolean };

function readNote(): RemovalNote | null {
  try {
    const v = localStorage.getItem(REMOVING);
    return v ? (JSON.parse(v) as RemovalNote) : null;
  } catch {
    return null;
  }
}

function note(value: RemovalNote | null) {
  try {
    if (value) localStorage.setItem(REMOVING, JSON.stringify(value));
    else localStorage.removeItem(REMOVING);
  } catch {
    /* storage off: the result then shows only when no reload happened */
  }
}

/** The note present when this page loaded: the only one startup recovery may resolve (B1). */
export const noteAtLoad: { at: number } | null = readNote();

/** A refusal from the app, worded so he sees why a removal talks about the engine (F6). */
export const removalRefusal = (r: LauncherRemoval) =>
  `Removing the old launcher restarts the engine. ${r.reason || "The old launcher couldn't be removed."}`;

/** The removal's card was closed (OK or Close): its result is consumed. */
export function removalConsumed() {
  note(null);
}

/** Resolve the note against the app's saved lastRemoval, only while the engine reads running, and
 * only the note the caller started from (its `at`, checked again here, just before anything is
 * cleared or claimed). null: no such note, or not yet decidable. "refused": nothing ran, and the
 * note is gone. A reloaded page claims the result (the note goes); the live page keeps it until its
 * card is closed. */
export function resolveRemoval(s: LauncherStatus, engineRunning: boolean, afterReload: boolean, at: number): Removal | "refused" | null {
  const n = readNote();
  if (!n || n.at !== at || !engineRunning) return null;
  const r = s.lastRemoval;
  const savedAt = r ? (typeof r.at === "number" ? r.at : Date.parse(r.at)) : NaN;
  if (r && savedAt >= n.at) {
    if (afterReload) note(null);
    return { result: r, before: n.before, afterReload };
  }
  note(null);
  return "refused";
}

/** Remove the old launcher: what to show, the result or the refusal's words. */
export async function removeOldLauncher(before: Pieces | null): Promise<{ shown: Removal } | { refused: string }> {
  const mine = { at: Date.now(), before };
  note(mine);
  const r = await own(() => desktop!.oldLauncher.remove());
  const engine = await desktop!.engineStatus().catch(() => null);
  if (engine?.state === "running") {
    // its own note only (mine.at): a refusal clears the note this click wrote, never another
    const res = resolveRemoval(await desktop!.oldLauncher.status(), engine.state === "running", false, mine.at);
    if (res === "refused") return { refused: removalRefusal(r) };
    if (res) return { shown: res };
  }
  // The engine is not running (it didn't start again, or a crash is being restarted): show what
  // remove() said; the note waits for the running engine, which settles it.
  return { shown: { result: r, before, afterReload: false } };
}
