/** Mac app only: Settings' "This Mac" section (mockup section 9), in place of Startup. */

import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import Modal from "./Modal";
import Toggle from "./Toggle";
import { RemovalResult, TerminalFlow } from "./MacCards";
import { desktop, occupantWords, otherCopyWords, removeOldLauncher, restartEngine, runningJobs, runsOurs, useEngineStatus } from "../desktop";
import type { DockMode, LauncherStatus, Removal, TerminalStatus } from "../desktop";

const SMALL_BTN =
  "inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs text-text-secondary hover:text-text hover:bg-surface-hover transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-text-secondary";
const LINK = "text-amber hover:underline cursor-pointer";
const CODE = "font-mono text-[11.5px] text-text";
const JOBS_POLL_MS = 3000;

const DOCK: { mode: DockMode; label: string; help: string; where: string }[] = [
  {
    mode: "menubar",
    label: "Menu bar",
    help: "When its window is closed, anyscribe stays in the menu bar only. The Dock icon shows while the window is open.",
    where: "the menu bar",
  },
  {
    mode: "both",
    label: "Menu bar and Dock",
    help: "anyscribe stays in both the menu bar and the Dock, like a normal app, even with its window closed.",
    where: "the menu bar and the Dock",
  },
  {
    mode: "dock",
    label: "Dock",
    help: "No menu bar icon. anyscribe stays in the Dock while it runs; click the Dock icon to open it.",
    where: "the Dock",
  },
];

function Row({ label, control, children }: { label: string; control?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1.5 py-3 border-b border-border-subtle last:border-b-0">
      <span className="text-sm text-text">{label}</span>
      {control ? <div className="justify-self-start sm:justify-self-end flex items-center gap-2">{control}</div> : <span className="hidden sm:block" />}
      <div className="sm:col-span-2 text-xs text-text-secondary leading-relaxed">{children}</div>
    </div>
  );
}

const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));

export default function ThisMac({ workspace }: { workspace?: string }) {
  const bridge = desktop!;
  const engine = useEngineStatus();
  const [settings, setSettings] = useState<{ dockMode: DockMode; startAtLogin: boolean } | null>(null);
  const [loginAsked, setLoginAsked] = useState(false); // turned on here, so a system "off" needs a word
  const [terminal, setTerminal] = useState<TerminalStatus | null>(null);
  const [conflict, setConflict] = useState<string | null>(null);
  const [skillRemoved, setSkillRemoved] = useState(false); // F8: this view's turnOff just removed it
  const [flow, setFlow] = useState(false); // the Terminal card, opened from a row
  const [launcher, setLauncher] = useState<LauncherStatus | null>(null);
  const [removal, setRemoval] = useState<Removal | null>(null); // with the pieces read before it (G4)
  const [jobs, setJobs] = useState<number | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [problem, setProblem] = useState<{ row: string; text: string } | null>(null);

  const readTerminal = useCallback(() => bridge.terminal.status().then(setTerminal), [bridge]);

  useEffect(() => {
    bridge.getSettings().then(setSettings).catch((e) => setProblem({ row: "dock", text: errText(e) }));
    readTerminal().catch((e) => setProblem({ row: "terminal", text: errText(e) }));
    bridge.oldLauncher.status().then(setLauncher).catch(() => setLauncher(null));
  }, [bridge, readTerminal]);

  // Restart engine waits for transcriptions: read the engine's job list while it runs.
  const engineRunning = engine?.state === "running";
  useEffect(() => {
    if (!engineRunning) return;
    let live = true;
    const read = () => runningJobs().then((n) => live && setJobs(n));
    read();
    const id = setInterval(read, JOBS_POLL_MS);
    return () => {
      live = false;
      clearInterval(id);
    };
  }, [engineRunning]);

  /** Run one row's action, showing its plain-words failure under that row. */
  const run = async (row: string, fn: () => Promise<void>) => {
    setBusy(row);
    setProblem(null);
    try {
      await fn();
    } catch (e) {
      setProblem({ row, text: errText(e) });
    } finally {
      setBusy(null);
    }
  };
  const failed = (row: string) =>
    problem?.row === row ? <p className="text-red mt-1">{problem.text}</p> : null;

  const setDock = (mode: DockMode) =>
    run("dock", async () => {
      await bridge.setDockMode(mode);
      setSettings(await bridge.getSettings());
    });
  const setLogin = (on: boolean) =>
    run("login", async () => {
      await bridge.setStartAtLogin(on);
      setLoginAsked(on);
      setSettings(await bridge.getSettings());
    });

  const turnOn = () =>
    run("terminal", async () => {
      const s = await bridge.terminal.turnOn({ replace: false });
      if (s.ok === false) throw new Error(s.reason || "anyscribe couldn't turn this on.");
      setTerminal(s);
    });
  const turnOff = (choice?: "keep-current" | "restore") =>
    run("terminal", async () => {
      const r = await bridge.terminal.turnOff(choice && { choice });
      if (r.needsChoice) {
        setConflict(r.reason || "The anyscribe command was changed since it was turned on.");
        return;
      }
      if (!r.ok) throw new Error(r.reason || "anyscribe couldn't turn this off.");
      setConflict(null);
      const had = terminal?.skill === "installed";
      const s = await bridge.terminal.status();
      setTerminal(s);
      setSkillRemoved(had && s.skill !== "installed");
    });
  const retrySkill = () =>
    run("terminal", async () => {
      const s = await bridge.terminal.retrySkill();
      if (s.ok === false) throw new Error(s.reason || "The skill still couldn't be installed.");
      setTerminal(s); // a reason that comes with ok shows as the row's information line
    });
  const removeLauncher = () =>
    run("launcher", async () => {
      const r = await removeOldLauncher(launcher?.pieces ?? null); // the app reloads the page: App shows the kept result
      if ("refused" in r) throw new Error(r.refused);
      setRemoval(r.shown);
      setLauncher(await bridge.oldLauncher.status());
    });
  const restart = () =>
    run("engine", async () => {
      const r = await restartEngine();
      if (!r.ok) throw new Error(r.reason || "The engine couldn't be restarted.");
    });

  const dock = DOCK.find((d) => d.mode === settings?.dockMode) ?? DOCK[0];
  const ours = !!terminal?.command;

  // ── Use from Terminal and Claude Code: one line per state ──
  let terminalLine: React.ReactNode = null;
  let terminalExtra: React.ReactNode = null;
  if (terminal) {
    const { name, via } = otherCopyWords(terminal);
    const other = `${name}${via ? `, installed ${via}` : ""}`;
    if (terminal.state === "on" && !runsOurs(terminal)) {
      // C5: written, but the login shell could not be asked; the reason shows below
      terminalLine = (
        <>
          <span className="text-amber">On.</span> The command is added; anyscribe couldn't check that Terminal finds it.
          {terminal.skill === "missing" && " The Claude Code skill isn't installed."}
        </>
      );
      if (terminal.skill === "missing")
        terminalExtra = <button onClick={retrySkill} disabled={!!busy} className={SMALL_BTN}>Try again</button>;
    } else if (terminal.state === "on") {
      if (terminal.skill === "missing") {
        terminalLine = <><span className="text-amber">On.</span> Terminal is ready; the Claude Code skill isn't installed.</>;
        terminalExtra = (
          <button onClick={retrySkill} disabled={!!busy} className={SMALL_BTN}>Try again</button>
        );
      } else {
        const skill = terminal.skill === "installed" ? "Claude Code skill installed." : "Claude Code isn't on this Mac.";
        terminalLine = (
          <>
            <span className="text-green">On.</span> Terminal runs this app's anyscribe {terminal.appVersion} from{" "}
            <code className={CODE}>{terminal.command}</code>. {skill}
          </>
        );
      }
    } else if (terminal.state === "path-missing") {
      terminalLine = <><span className="text-amber">On.</span> Terminal can't see the command yet: it doesn't look in <code className={CODE}>~/.local/bin</code>.</>;
      terminalExtra = (
        <button onClick={() => setFlow(true)} disabled={!!busy} className={SMALL_BTN}>Add it for me</button>
      );
    } else if (terminal.state === "other-copy") {
      // ours written but another first: the status reason says where ("Terminal finds another anyscribe at <path> first.")
      terminalLine = ours ? (
        <span className="text-amber">On.</span>
      ) : (
        <>
          <span className="text-amber">Off.</span> Terminal uses another {other}.{" "}
          {terminal.occupant && (
            <button onClick={() => setFlow(true)} className={LINK}>Switch to this app's copy</button>
          )}
        </>
      );
    } else if (terminal.occupant) {
      // F5: a copy sits at ~/.local/bin/anyscribe that Terminal does not use
      terminalLine = (
        <>
          Off. {occupantWords(terminal)}{" "}
          <button onClick={() => setFlow(true)} className={LINK}>Switch to this app's copy</button>
        </>
      );
    } else {
      terminalLine = <>Off. anyscribe isn't in Terminal{skillRemoved ? ", and its Claude Code skill is removed" : ""}.</>;
    }
  }
  const toggleTerminal = (on: boolean) => {
    if (!on) return void turnOff();
    if (terminal?.occupant) return setFlow(true); // replacing another copy asks first
    void turnOn();
  };

  // ── Engine ──
  const running = engineRunning ? jobs ?? 0 : 0;
  const restartBlocked = engineRunning && running > 0;
  const engineWords = !engine ? null : engine.stoppedRestarting ? (
    <>
      <span className="text-red">Stopped.</span> It stopped 3 times in a minute, so anyscribe stopped restarting it.{" "}
      <button onClick={() => document.querySelector("main")?.scrollTo({ top: 0, behavior: "smooth" })} className={LINK}>
        What happened
      </button>
    </>
  ) : engine.state === "running" ? (
    <>
      <span className="text-green">Running{running > 0 ? ` · ${running} ${running === 1 ? "transcription" : "transcriptions"}` : ""}.</span>{" "}
      {restartBlocked && "Wait for transcriptions to finish before restarting the engine. "}
      <button onClick={() => void bridge.openLogFolder()} className={LINK}>Open log folder</button>
    </>
  ) : (
    <>
      <span className="text-amber">{{ starting: "Starting.", restarting: "Restarting.", stopped: "Stopped." }[engine.state]}</span>{" "}
      <button onClick={() => void bridge.openLogFolder()} className={LINK}>Open log folder</button>
    </>
  );

  const showLauncher = !!launcher?.installed || !!removal;

  return (
    <section className="mb-10" id="this-mac">
      <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">This Mac</h2>
      <div className="rounded-lg border border-border-subtle bg-surface px-4 py-1">
        <Row
          label="Show anyscribe in"
          control={
            <div role="group" aria-label="Show anyscribe in" className="inline-flex flex-wrap gap-0.5 rounded-lg border border-border bg-bg p-0.5">
              {DOCK.map((d) => (
                <button
                  key={d.mode}
                  aria-pressed={settings?.dockMode === d.mode}
                  disabled={!settings || busy === "dock"}
                  onClick={() => d.mode !== settings?.dockMode && setDock(d.mode)}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
                    settings?.dockMode === d.mode
                      ? "bg-surface-raised text-text shadow-[inset_0_0_0_1px_var(--color-border)]"
                      : "text-text-secondary hover:text-text"
                  }`}
                >
                  {d.label}
                </button>
              ))}
            </div>
          }
        >
          {settings && dock.help}
          {failed("dock")}
        </Row>

        <Row
          label="Start at login"
          control={
            <Toggle
              label="Start at login"
              value={!!settings?.startAtLogin}
              disabled={!settings || busy === "login"}
              onChange={(v) => void setLogin(v)}
            />
          }
        >
          {settings &&
            (settings.startAtLogin
              ? `On. anyscribe starts in ${dock.where} when you log in, with no window.`
              : `Off. When on, anyscribe starts in ${dock.where} when you log in, with no window.`)}
          {settings && loginAsked && !settings.startAtLogin && (
            <p className="text-amber mt-1">
              macOS hasn't turned it on yet. If it asks, allow anyscribe in System Settings, under Login Items.
            </p>
          )}
          {failed("login")}
        </Row>

        <Row
          label="Use from Terminal and Claude Code"
          control={
            <>
              {terminalExtra}
              <Toggle
                label="Use from Terminal and Claude Code"
                value={ours}
                disabled={!terminal || !!busy}
                onChange={toggleTerminal}
              />
            </>
          }
        >
          {terminalLine}
          {terminal?.reason && <p className="mt-1">{terminal.reason}</p>}
          {conflict && (
            <div className="mt-2 rounded-md border border-amber/40 bg-amber/[0.08] px-3 py-2">
              <p className="text-text">{conflict}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <button onClick={() => void turnOff("keep-current")} disabled={!!busy} className={SMALL_BTN}>Keep current command</button>
                <button onClick={() => void turnOff("restore")} disabled={!!busy} className={SMALL_BTN}>Restore previous command</button>
              </div>
            </div>
          )}
          {failed("terminal")}
        </Row>

        <Row label="Updates">
          Version <span className="font-mono">{bridge.version}</span>.
        </Row>

        <Row
          label="Engine"
          control={
            <button onClick={restart} disabled={restartBlocked || busy === "engine"} className={SMALL_BTN}>
              <RefreshCw className="w-3 h-3" />
              Restart engine
            </button>
          }
        >
          {engineWords}
          {failed("engine")}
        </Row>

        {showLauncher && (
          <Row
            label="Old browser launcher"
            control={
              launcher?.installed && (
                <button onClick={removeLauncher} disabled={busy === "launcher"} className={SMALL_BTN}>Remove it</button>
              )
            }
          >
            {launcher?.installed && (
              <>
                Still installed in <code className={CODE}>~/Applications</code>
                {launcher.pieces.loginItem === "present" ? ", with its login item" : ""}. Your transcripts and settings
                are not affected.
              </>
            )}
            {removal && (
              <div className="mt-2 rounded-lg border border-border bg-surface-raised px-4 py-3">
                <RemovalResult removal={removal} onRetry={removeLauncher} busy={busy === "launcher"} />
              </div>
            )}
            {failed("launcher")}
          </Row>
        )}

        <Row label="Removing anyscribe">
          Turn off Start at login and Use from Terminal and Claude Code, quit anyscribe, then drag it from
          Applications to the Trash. Your transcripts in <code className={CODE}>{workspace || "~/anyscribe"}</code> and
          settings in <code className={CODE}>~/.anyscribe</code> stay. Downloaded local models stay too; to free that
          space, use Remove local transcription in Settings before you remove the app.
        </Row>
      </div>

      {flow && (
        <Modal
          onClose={() => {
            setFlow(false);
            void readTerminal();
          }}
          ariaLabel="Terminal and Claude Code"
          size="lg"
        >
          <TerminalFlow
            onDone={() => {
              setFlow(false);
              void readTerminal();
            }}
          />
        </Modal>
      )}
    </section>
  );
}
