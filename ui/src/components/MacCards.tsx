/** Mac app only: the old-launcher question and the Terminal and Claude Code
 * cards (mockup sections 3 and 4). Used on first launch, as the setup wizard's
 * last step, and from Settings' This Mac rows. */

import { useEffect, useState } from "react";
import { AlertCircle, Check, Loader2 } from "lucide-react";
import { desktop, markAsked, occupantWords, otherCopyWords, removalConsumed, removeOldLauncher, runsOurs, VIA } from "../desktop";
import type { LauncherRemoval, LauncherStatus, Pieces, Removal, TerminalStatus } from "../desktop";

export const BTN_MAIN =
  "rounded-md bg-amber text-surface px-3.5 py-1.5 text-sm font-medium hover:bg-amber/80 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed";
export const BTN_QUIET =
  "rounded-md border border-border px-3.5 py-1.5 text-sm text-text-secondary hover:text-text hover:bg-surface-hover transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed";
const BTN_LINK = "text-sm text-text-secondary hover:text-text underline cursor-pointer";
const CODE = "font-mono text-[12.5px] text-text";

export function Card({
  eyebrow,
  tone,
  title,
  children,
}: {
  eyebrow?: string;
  tone?: "ok" | "warn" | "bad";
  title: string;
  children: React.ReactNode;
}) {
  const icon =
    tone === "ok" ? <Check className="w-4.5 h-4.5 text-green shrink-0" /> :
    tone === "warn" ? <AlertCircle className="w-4.5 h-4.5 text-amber shrink-0" /> :
    tone === "bad" ? <AlertCircle className="w-4.5 h-4.5 text-red shrink-0" /> : null;
  return (
    <div className="flex flex-col gap-3 text-sm text-text-secondary [&_b]:text-text [&_b]:font-semibold">
      {eyebrow && (
        <span className="font-mono text-[11.5px] uppercase tracking-[0.1em] text-amber">{eyebrow}</span>
      )}
      <div className="flex items-center gap-2">
        {icon}
        <h3 className="text-base font-semibold text-text" style={{ fontFamily: "var(--font-display)" }}>
          {title}
        </h3>
      </div>
      {children}
    </div>
  );
}

const Buttons = ({ children }: { children: React.ReactNode }) => (
  <div className="flex flex-wrap items-center gap-2 pt-1">{children}</div>
);
const Note = ({ children }: { children: React.ReactNode }) => (
  <p className="text-[12.5px] text-text-secondary">{children}</p>
);
const Problem = ({ text }: { text: string | null | undefined }) =>
  text ? <p className="text-xs text-red">{text}</p> : null;

// ── Old browser launcher ─────────────────────────────

const PIECE_WORDS: [keyof NonNullable<LauncherRemoval["pieces"]>, string, string][] = [
  ["launcher", "Launcher", "removed"],
  ["loginItem", "Login item", "removed"],
  ["menuBarIcon", "Old menu bar icon", "stopped"],
];

/** "Removed the old launcher, its login item and its menu bar icon.": only what was there before,
 * from the pieces read before the removal (A5, G4). */
function removedWords(before: Pieces | null): string {
  if (!before) return "Cleanup finished. Nothing of the old launcher is left on this Mac.";
  const launcher = before.launcher === "present";
  const login = before.loginItem === "present";
  const icon = before.menuBarIcon === "running";
  if (!launcher && !login && icon) return "Stopped the old menu bar icon. The launcher and login item were already gone.";
  const parts = [
    launcher && "the old launcher",
    login && (launcher ? "its login item" : "the old login item"),
    icon && (launcher ? "its menu bar icon" : "the old menu bar icon"),
  ].filter(Boolean) as string[];
  if (!parts.length) return "Cleanup finished. Nothing of the old launcher is left on this Mac.";
  const list = parts.length > 1 ? `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}` : parts[0];
  return `Removed ${list}.`;
}

/** The result's own reason; claimed after a reload, a "didn't start again" is out of date. */
function reasonWords(r: LauncherRemoval, afterReload: boolean): string | null {
  if (!r.reason) return null;
  if (!afterReload || !/didn't start again/.test(r.reason)) return r.reason;
  return `${r.reason}${/[.!?]$/.test(r.reason) ? "" : "."} It is running again now.`; // the engine's reason often ends bare (K4)
}

/** The result of a removal: "Removed", the cleanup checklist, or (no pieces) the reason alone. */
export function RemovalResult({
  removal,
  onRetry,
  onDone,
  busy,
}: {
  removal: Removal;
  onRetry: () => void;
  onDone?: () => void;
  busy: boolean;
}) {
  const { result, before, afterReload } = removal;
  const reason = reasonWords(result, afterReload);
  const [copied, setCopied] = useState(false);
  const done = onDone && (() => {
    removalConsumed();
    onDone();
  });
  if (result.ok) {
    return (
      <Card tone="ok" title="Old launcher removed">
        <p>
          {removedWords(before)}
          {result.startAtLoginCarriedOver && " This app now starts at login instead; change it in Settings."}
        </p>
        {reason && <p>{reason /* always: it can say the engine didn't start again (A3, G3) */}</p>}
        {done && (
          <Buttons>
            <button autoFocus onClick={done} className={BTN_MAIN}>OK</button>
          </Buttons>
        )}
      </Card>
    );
  }
  const retryButtons = (
    <>
      <button onClick={onRetry} disabled={busy} className={BTN_MAIN}>
        {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin inline" /> : "Try again"}
      </button>
      {done && <button onClick={done} className={BTN_LINK}>Close</button>}
    </>
  );
  if (!result.pieces) {
    // the removal itself failed (the app kept {ok: false, pieces: null, reason}): its reason alone
    return (
      <Card tone="bad" title="Cleanup didn't finish">
        <p>{reason || "The old launcher couldn't be removed."}</p>
        <Buttons>{retryButtons}</Buttons>
      </Card>
    );
  }
  const pieces = result.pieces;
  // the bridge's reason opens with "Cleanup didn't finish: <what is left>.", which the title and checklist say (K1)
  const extra = reason?.replace(/^Cleanup didn't finish: [^.]*\.\s*/, "") || null;
  const copy = async () => {
    const lines = PIECE_WORDS.map(([k, label]) => `${label}: ${pieces[k]}`);
    if (result.reason) lines.push(`Reason: ${result.reason}`);
    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* the checklist is on screen anyway */
    }
  };
  return (
    <Card tone="bad" title="Cleanup didn't finish">
      <ul className="flex flex-col gap-1.5">
        {PIECE_WORDS.map(([k, label, good]) => {
          const ok = pieces[k] === good;
          return (
            <li key={k} className="flex items-center gap-2">
              {ok ? <Check className="w-3.5 h-3.5 text-green" /> : <AlertCircle className="w-3.5 h-3.5 text-red" />}
              <span>
                {label}: <b>{pieces[k]}</b>
              </span>
            </li>
          );
        })}
      </ul>
      <p>
        {pieces.menuBarIcon === "still running"
          ? "Log out and back in to stop it, or try again."
          : "Try again. If it still doesn't finish, Copy details shows what was left."}
      </p>
      {extra && <p>{extra /* what the bridge adds (B2), below the advice so its "it" stays the icon (K1) */}</p>}
      <Buttons>
        {retryButtons}
        <button onClick={copy} className={BTN_LINK}>{copied ? "Copied" : "Copy details"}</button>
      </Buttons>
    </Card>
  );
}

/** The result of a removal this page started, read from lastRemoval after the reload. */
export function RemovalAfterReload({ initial, onDone }: { initial: Removal; onDone: () => void }) {
  const [removal, setRemoval] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const retry = async () => {
    setBusy(true);
    setProblem(null);
    try {
      const r = await removeOldLauncher(initial.before);
      if ("refused" in r) setProblem(r.refused);
      else setRemoval(r.shown);
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <RemovalResult removal={removal} onRetry={retry} onDone={onDone} busy={busy} />
      <Problem text={problem} />
    </>
  );
}

/** First launch: replace the old launcher, or keep both. Marks the question asked on either answer. */
export function LauncherQuestion({ status, onDone }: { status: LauncherStatus; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Removal | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const login = status.pieces.loginItem === "present";

  const remove = async () => {
    setBusy(true);
    setProblem(null);
    try {
      await markAsked("oldLauncherAsked"); // a failed save is shown; the removal still runs
      const r = await removeOldLauncher(status.pieces); // the app reloads the page: App shows the kept result
      if ("refused" in r) setProblem(r.refused);
      else setResult(r.shown);
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  const keep = async () => {
    await markAsked("oldLauncherAsked");
    onDone();
  };

  if (result) return <RemovalResult removal={result} onRetry={remove} onDone={onDone} busy={busy} />;
  return (
    <Card title="Replace the old anyscribe launcher?">
      <p>
        This Mac also has the earlier anyscribe launcher in <code className={CODE}>~/Applications</code>
        {login ? " and a login item that starts it" : ""}. It opens anyscribe in your browser. This app
        does the same job, so you only need one.{login ? " This app will start at login in its place." : ""}
      </p>
      <p>
        <b>Your transcripts, settings and API keys stay where they are.</b>
      </p>
      <Problem text={problem} />
      <Buttons>
        <button onClick={remove} disabled={busy} className={BTN_MAIN}>
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin inline" /> : "Remove the old launcher"}
        </button>
        <button onClick={keep} disabled={busy} className={BTN_QUIET}>Keep both</button>
      </Buttons>
      <Note>
        Keeping both shows two anyscribe icons in the menu bar. You won't be asked again; Settings
        keeps a Remove button while it is installed.
      </Note>
    </Card>
  );
}

// ── Terminal and Claude Code ─────────────────────────

type View = "loading" | "offer" | "switch" | "other" | "on" | "skill" | "path" | "added-but-missing";

function viewFor(s: TerminalStatus): View {
  if (s.state === "off") return s.occupant ? "switch" : "offer"; // F5: a copy sits at our spot, unused
  if (s.state === "other-copy") return "other";
  if (s.state === "path-missing") return "path";
  return s.skill === "missing" ? "skill" : "on";
}

/** The Terminal question and its outcomes. Starts from terminal.status(); `onDone`
 * runs on the person's last answer (Skip, Keep, Done, Continue, I'll do it myself). */
export function TerminalFlow({ eyebrow, onDone }: { eyebrow?: string; onDone: () => void }) {
  const [status, setStatus] = useState<TerminalStatus | null>(null);
  const [view, setView] = useState<View>("loading");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [byHand, setByHand] = useState<{ line: string; reason: string } | null>(null); // addToPath refused (F4)
  const [addedReason, setAddedReason] = useState<string | null>(null); // addToPath ok, with why it has no effect (F3)

  useEffect(() => {
    desktop!.terminal
      .status()
      .then((s) => {
        setStatus(s);
        setView(viewFor(s));
      })
      .catch((e) => {
        setProblem(e instanceof Error ? e.message : String(e));
        setView("offer");
      });
  }, []);

  const act = async (call: () => Promise<TerminalStatus>, next?: (s: TerminalStatus) => View) => {
    setBusy(true);
    setProblem(null);
    try {
      const s = await call();
      if (s.ok === false) {
        setProblem(s.reason || "That didn't work.");
      } else {
        setStatus(s);
        setView(next ? next(s) : viewFor(s));
      }
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  const turnOn = (replace: boolean) => act(() => desktop!.terminal.turnOn({ replace }));
  const addToPath = async () => {
    setBusy(true);
    setProblem(null);
    try {
      const r = await desktop!.terminal.addToPath();
      if (!r.ok) {
        // with a line, it is guidance (add it by hand); without one, a failure
        if (r.line) setByHand({ line: r.line, reason: r.reason || "Add this line by hand:" });
        else setProblem(r.reason || "anyscribe couldn't add the line.");
        return;
      }
      setAddedReason(r.reason || null);
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
      return;
    } finally {
      setBusy(false);
    }
    await act(() => desktop!.terminal.status(), (s) => (s.state === "path-missing" ? "added-but-missing" : viewFor(s)));
  };

  const spin = <Loader2 className="w-3.5 h-3.5 animate-spin inline" />;

  if (view === "loading") return <Loader2 className="w-4 h-4 animate-spin text-text-muted" />;

  if (view === "offer")
    return (
      <Card eyebrow={eyebrow} title="Use anyscribe from Terminal and Claude Code">
        <p>
          Puts the <code className={CODE}>anyscribe</code> command on this Mac, so you can run it in
          Terminal, and Claude Code can transcribe links for you when you ask.
        </p>
        <ul className="list-disc pl-5 flex flex-col gap-0.5">
          <li>Adds one small file: <code className={CODE}>~/.local/bin/anyscribe</code></li>
          <li>Installs the anyscribe skill for Claude Code, if Claude Code is on this Mac</li>
          <li>Turn it off any time in Settings</li>
        </ul>
        <Problem text={problem} />
        <Buttons>
          <button onClick={() => turnOn(false)} disabled={busy} className={BTN_MAIN}>{busy ? spin : "Turn on"}</button>
          <button onClick={onDone} disabled={busy} className={BTN_QUIET}>Skip for now</button>
        </Buttons>
      </Card>
    );

  if (view === "switch" && status)
    return (
      <Card eyebrow={eyebrow} title="Use anyscribe from Terminal and Claude Code">
        <p>{occupantWords(status)}</p>
        <ul className="list-disc pl-5 flex flex-col gap-0.5">
          <li>Installs the anyscribe skill for Claude Code, if Claude Code is on this Mac</li>
          <li>Turn it off any time in Settings</li>
        </ul>
        <Problem text={problem} />
        <Buttons>
          <button onClick={() => turnOn(true)} disabled={busy} className={BTN_MAIN}>{busy ? spin : "Switch to this app's copy"}</button>
          <button onClick={onDone} disabled={busy} className={BTN_QUIET}>Skip for now</button>
        </Buttons>
        <Note>
          If you switch, turning this off later puts your {VIA[status.occupant!.via] ? `${status.occupant!.via} ` : ""}
          copy back, unless something has replaced the command since; then it asks first.
        </Note>
      </Card>
    );

  if (view === "other" && status) {
    const { name, via } = otherCopyWords(status);
    return (
      <Card eyebrow={eyebrow} title="Terminal already has anyscribe">
        <p>
          Terminal uses <b>{name}</b>, installed separately{via ? ` ${via}` : ""}
          {status.uses && <> at <code className={CODE}>{status.uses.path}</code></>}. Both copies use the
          same transcripts, settings and keys.
        </p>
        {status.occupant ? (
          <p>Keep it if you update it yourself. Switch to have it update with this app instead.</p>
        ) : (
          status.reason && <p>{status.reason}</p>
        )}
        {status.claudeCode && <p>Claude Code keeps using that copy and its skill.</p>}
        <Problem text={problem} />
        <Buttons>
          <button onClick={onDone} disabled={busy} className={BTN_MAIN}>
            {status.occupant ? "Keep the one I have" : "OK" /* F16: nothing to choose between */}
          </button>
          {status.occupant && (
            <button onClick={() => turnOn(true)} disabled={busy} className={BTN_QUIET}>
              {busy ? spin : "Switch to this app's copy"}
            </button>
          )}
        </Buttons>
        {status.occupant && (
          <Note>
            If you switch, turning this off later puts your {VIA[status.occupant.via] ? `${status.occupant.via} ` : ""}
            copy back, unless something has replaced the command since; then it asks first.
          </Note>
        )}
      </Card>
    );
  }

  if (view === "skill" && status)
    return (
      <Card
        tone="warn"
        title={
          runsOurs(status)
            ? "Terminal is ready, but the Claude Code skill couldn't be installed"
            : "The anyscribe command is added, but the Claude Code skill couldn't be installed"
        }
      >
        {status.reason && <p>{status.reason}</p>}
        <Problem text={problem} />
        <Buttons>
          <button onClick={() => act(() => desktop!.terminal.retrySkill())} disabled={busy} className={BTN_MAIN}>
            {busy ? spin : "Try again"}
          </button>
          <button onClick={onDone} disabled={busy} className={BTN_QUIET}>Continue</button>
        </Buttons>
      </Card>
    );

  if (view === "path" || view === "added-but-missing")
    return (
      <Card tone="warn" title="One more step for Terminal">
        {view === "added-but-missing" ? (
          <p>{addedReason || "The line was added, but Terminal still can't see the command."}</p>
        ) : byHand ? (
          // the app's reason often ends with the line itself: say it once, in the box (G6)
          <p>{byHand.reason.endsWith(byHand.line) ? byHand.reason.slice(0, -byHand.line.length).trimEnd() : byHand.reason}</p>
        ) : (
          <p>
            The command is in <code className={CODE}>~/.local/bin</code>, but your Terminal doesn't look in
            that folder yet. anyscribe can add this line to <code className={CODE}>~/.zprofile</code> (
            <code className={CODE}>~/.bash_profile</code> if your Terminal uses bash):
          </p>
        )}
        <pre className="select-all rounded-lg border border-border-subtle bg-[#08070B] px-3 py-2.5 font-mono text-[11.5px] text-text-secondary overflow-x-auto">
          {byHand ? byHand.line : 'export PATH="$HOME/.local/bin:$PATH"'}
        </pre>
        {status?.reason && <Note>{status.reason}</Note>}
        <Problem text={problem} />
        <Buttons>
          {view === "path" && !byHand && (
            <button onClick={addToPath} disabled={busy} className={BTN_MAIN}>{busy ? spin : "Add it for me"}</button>
          )}
          <button onClick={onDone} disabled={busy} className={BTN_QUIET}>I'll do it myself</button>
        </Buttons>
        {view === "path" && (
          <Note>Takes effect in new Terminal windows. Claude Code picks it up the next time it starts.</Note>
        )}
      </Card>
    );

  if (!runsOurs(status))
    // C5: the command is written but the login shell could not be asked: no "ready" claim
    return (
      <Card tone="warn" title="The anyscribe command is added">
        {status?.reason && <p>{status.reason}</p>}
        <p>
          Open a new Terminal window and type <code className={CODE}>anyscribe --help</code> to check.
        </p>
        <Buttons>
          <button autoFocus onClick={onDone} className={BTN_MAIN}>Done</button>
        </Buttons>
      </Card>
    );

  return (
    <Card tone="ok" title="anyscribe is ready in Terminal">
      <p>
        Open a new Terminal window and type <code className={CODE}>anyscribe --help</code>.
        {status?.claudeCode && " In Claude Code, ask it to transcribe a link."}
      </p>
      {status?.reason && <Note>{status.reason}</Note>}
      <Note>It runs this app's anyscribe {status?.appVersion} and updates with the app.</Note>
      {!status?.claudeCode && (
        <Note>If Claude Code isn't on this Mac yet, turn this off and on again after installing it to add the skill.</Note>
      )}
      <Buttons>
        <button autoFocus onClick={onDone} className={BTN_MAIN}>Done</button>
      </Buttons>
    </Card>
  );
}
