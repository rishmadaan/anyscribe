/** Mac app only: the engine trouble banner at the top of every page (mockup section 10). */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, Check, RefreshCw } from "lucide-react";
import { desktop, exitWords, GUIDE_URL, OUTAGE, restartEngine, restartIsMine, session } from "../desktop";
import type { EngineStatus } from "../desktop";

const BTN_MAIN =
  "rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-medium hover:bg-amber/80 transition-colors cursor-pointer";
const BTN_LINK = "text-xs text-text-secondary hover:text-text underline cursor-pointer";

/** `watching` names the job the Transcribe page is following right now, or null. */
export default function EngineBanner({ watching }: { watching: { current: string | null } }) {
  const [status, setStatus] = useState<EngineStatus | null>(null);
  const [backAgain, setBackAgain] = useState<{ job: string | null } | null>(null);
  const [refused, setRefused] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [mine, setMine] = useState(false); // this page asked for the restart

  useEffect(() => {
    if (!desktop) return;
    // The app reloads this page to / when the engine is back (2c-app main.js), so an outage is
    // noted in sessionStorage: the reloaded page shows "Running again", naming the job watched
    // when the engine stopped. A restart this page asked for is not an outage.
    let wasRunning = false;
    let first = true;
    let live = true;
    const onStatus = (s: EngineStatus) => {
      if (!live) return;
      setStatus(s);
      const asked = restartIsMine();
      setMine(asked);
      if (s.state === "running") {
        setRefused(null);
        const note = session.get<{ job: string | null }>(OUTAGE);
        if (note) setBackAgain({ job: note.job });
        // a fresh page takes the note; an older page leaves it for the reload that follows
        if (first) session.del(OUTAGE);
      } else if ((wasRunning || s.state === "restarting") && !asked && !session.get(OUTAGE)) {
        session.set(OUTAGE, { job: watching.current, at: Date.now() });
        setBackAgain(null);
      }
      wasRunning = s.state === "running";
      first = false;
    };
    desktop.engineStatus().then(onStatus).catch(() => undefined);
    const off = desktop.onEngineStatus(onStatus);
    return () => {
      live = false;
      off();
    };
  }, [watching]);

  if (!desktop || !status) return null;

  const wrap = (tone: string, icon: React.ReactNode, body: React.ReactNode) => (
    <div role="status" className={`mx-6 mt-6 rounded-lg border px-4 py-3 flex gap-2.5 items-start animate-slide-up ${tone}`}>
      {icon}
      <div className="flex flex-col gap-2 min-w-0">{body}</div>
    </div>
  );

  // Keeps stopping, or stopped and not restarting (a restart that failed): the same red card.
  if (status.stoppedRestarting || status.state === "stopped") {
    const keeps = status.stoppedRestarting;
    const restart = async () => {
      setRefused(null);
      const r = await restartEngine();
      if (!r.ok) setRefused(r.reason || "The engine couldn't be restarted.");
    };
    const copy = async () => {
      const details = [
        `anyscribe app ${desktop!.version} (${desktop!.platform})`,
        keeps ? `Engine: ${status.state}, stopped restarting after repeated exits` : "Engine: stopped, couldn't start again",
        `Last exit: code ${status.lastExit?.code ?? "none"}, signal ${status.lastExit?.signal ?? "none"}`,
        `Reason: ${status.lastExit?.reason ?? "not reported"}`,
        "Log: ~/.anyscribe/logs/app.log",
      ].join("\n");
      try {
        await navigator.clipboard.writeText(details);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch {
        setRefused("Couldn't copy the details.");
      }
    };
    return wrap(
      "border-red/45 bg-red/[0.08]",
      <AlertCircle className="w-4 h-4 text-red shrink-0 mt-0.5" />,
      <>
        <h3 className="text-sm font-medium text-text">
          {keeps ? "The engine keeps stopping" : "anyscribe's engine stopped"}
        </h3>
        <p className="text-[13px] text-text-secondary">
          {keeps
            ? "It stopped 3 times in a minute, so anyscribe stopped restarting it. "
            : "It couldn't start again. "}
          Your transcripts are safe. {exitWords(status.lastExit)}.
        </p>
        {refused && <p className="text-xs text-red">{refused}</p>}
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={restart} className={BTN_MAIN}>Restart engine</button>
          <button onClick={copy} className={BTN_LINK}>{copied ? "Copied" : "Copy details"}</button>
          <button onClick={() => void desktop!.openLogFolder()} className={BTN_LINK}>Open log folder</button>
          <a href={GUIDE_URL} target="_blank" rel="noopener noreferrer" className={BTN_LINK}>
            Troubleshooting guide
          </a>
        </div>
      </>
    );
  }

  if (status.state === "restarting") {
    return wrap(
      "border-amber/45 bg-amber/[0.08]",
      <RefreshCw className="w-4 h-4 text-amber shrink-0 mt-0.5" />,
      <>
        <h3 className="text-sm font-medium text-text">
          {mine ? "Restarting anyscribe's engine." : "anyscribe's engine stopped. Restarting it."}
        </h3>
        <p className="text-[13px] text-text-secondary">This usually takes a few seconds.</p>
      </>
    );
  }

  if (status.state === "running" && backAgain) {
    const dismiss = () => {
      session.del(OUTAGE);
      setBackAgain(null);
    };
    return wrap(
      "border-green/40 bg-green/[0.07]",
      <Check className="w-4 h-4 text-green shrink-0 mt-0.5" />,
      <>
        <h3 className="text-sm font-medium text-text">Running again</h3>
        {backAgain.job && (
          <p className="text-[13px] text-text-secondary">
            We couldn't confirm whether this transcription finished:{" "}
            <b className="text-text break-all">{backAgain.job}</b>. Check History before starting it again.
          </p>
        )}
        <div className="flex flex-wrap items-center gap-3">
          {backAgain.job && (
            <Link to="/history" onClick={dismiss} className={BTN_MAIN}>Open History</Link>
          )}
          <button onClick={dismiss} className={BTN_LINK}>Dismiss</button>
        </div>
      </>
    );
  }

  return null;
}
