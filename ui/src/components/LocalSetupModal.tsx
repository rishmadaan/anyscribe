/** Local transcription setup modal.
 *
 * Lets the user pick a model (recommended preselected; "Help me choose" asks
 * one question and suggests one) with the shared LocalModelPicker, kicks
 * off the unified backend setup flow, polls status until done, and streams
 * the install log into a collapsible panel so diagnostic output is visible
 * when something goes wrong.
 */

import { useEffect, useRef, useState } from "react";
import { X, Loader2, AlertCircle, Check, ChevronDown, ChevronRight } from "lucide-react";
import {
  getLocalStatus,
  setupLocal,
  getSetupLog,
  updateConfig,
} from "../api/client";
import type { LocalRecommendation, LocalStatusResponse } from "../api/types";
import Modal from "./Modal";
import LocalModelPicker from "./LocalModelPicker";
import { ExtraDownloads, RestartBanner } from "./LocalSetupNotes";
import { downloadMbFor, formatMB } from "../api/models";

const POLL_MS = 1500;
const MB = 1024 * 1024;

interface Props {
  onClose: () => void;
  onDone: () => void;
}

export default function LocalSetupModal({ onClose, onDone }: Props) {
  const [status, setStatus] = useState<LocalStatusResponse | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [logOpen, setLogOpen] = useState(false);
  const logCursorRef = useRef(0);
  // Extra downloads from "Help me choose" (Turbo for a language mix): sent
  // with setup, which queues them; the modal then stays open to show them.
  const [rec, setRec] = useState<LocalRecommendation | null>(null);
  const [finished, setFinished] = useState<{ also: string[] } | null>(null);

  // Initial status fetch + preselect recommended size.
  useEffect(() => {
    let cancelled = false;
    getLocalStatus()
      .then((s) => {
        if (cancelled) return;
        setStatus(s);
        setSelected((prev) => prev ?? s.recommended_model);
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load status")
      );
    return () => {
      cancelled = true;
    };
  }, []);

  // Poll status + log while setup is in flight.
  useEffect(() => {
    if (!status?.setup_running) return;
    const id = setInterval(async () => {
      try {
        const [s, log] = await Promise.all([
          getLocalStatus(),
          getSetupLog(logCursorRef.current),
        ]);
        setStatus(s);
        if (log.lines.length > 0) {
          setLogLines((prev) => [...prev, ...log.lines]);
          logCursorRef.current = log.total;
        }
        if (!s.setup_running) {
          clearInterval(id);
          if (s.setup_error) {
            setError(s.setup_error);
            setLogOpen(true);
          } else if (s.set_up) {
            const also = s.setup_also; // queued by the server
            if (also.length === 0 && !s.restart_needed && !s.use_local_tip) onDone();
            else setFinished({ also });
          }
        }
      } catch {
        // transient — keep polling
      }
    }, POLL_MS);
    return () => clearInterval(id);
  }, [status?.setup_running, onDone]);

  const handleDownload = async () => {
    if (!selected) return;
    setStarting(true);
    setError(null);
    setLogLines([]);
    logCursorRef.current = 0;
    try {
      await setupLocal(selected, rec && rec.primary === selected ? rec.also : []);
      const s = await getLocalStatus();
      setStatus(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start setup");
    } finally {
      setStarting(false);
    }
  };

  if (!status) {
    return (
      <Modal onClose={onClose} ariaLabel="Set up local transcription" size="lg">
        <div className="flex items-center justify-center py-10">
          <Loader2 className="w-5 h-5 animate-spin text-text-muted" />
        </div>
      </Modal>
    );
  }

  const running = status.setup_running;
  const phase = status.setup_phase;
  const selectedSpec = status.models.find((m) => m.size === selected)?.spec;
  // What the button downloads: the pick, a mix's second model (when the
  // suggestion was kept) and, for Parakeet, the Tiny language check.
  const keptRec = rec && rec.primary === selected ? rec : null;
  const toFetch = [selected, ...(keptRec?.also ?? [])].filter(Boolean) as string[];
  const downloadMb = downloadMbFor(status.models, toFetch);
  const names = toFetch
    .map((id) => status.models.find((m) => m.size === id)?.spec.display_name ?? id)
    .join(" + ");

  if (finished) {
    return (
      <Modal onClose={onDone} ariaLabelledBy="local-setup-title" size="lg">
        <h2
          id="local-setup-title"
          className="text-lg font-bold text-text mb-4"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Local transcription is set up
        </h2>
        {status.restart_needed && <RestartBanner />}
        <p className="text-sm text-text-secondary mb-3 flex items-center gap-1.5">
          <Check className="w-4 h-4 text-green" />
          {status.models.find((m) => m.size === status.default_model)?.spec.display_name ??
            status.default_model}{" "}
          is ready and is your default{status.use_local_tip ? " local model" : ""}.
        </p>
        {status.use_local_tip && (
          <p className="text-sm text-text-secondary mb-3">{status.use_local_tip}</p>
        )}
        {finished.also.length > 0 && (
          <div className="rounded-md border border-border-subtle bg-surface-raised px-3 py-2.5 mb-4">
            <ExtraDownloads
              ids={finished.also}
              name={(id) => status.models.find((m) => m.size === id)?.spec.display_name ?? id}
              pendingNote="Switching to it for Hindi and other languages works once it finishes downloading. You can close this; the download carries on in Settings."
            />
          </div>
        )}
        <div className="flex justify-end">
          <button
            onClick={onDone}
            className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal
      onClose={onClose}
      disableClose={running}
      ariaLabelledBy="local-setup-title"
      size="lg"
    >
      <div className="flex items-center justify-between mb-4">
        <h2
          id="local-setup-title"
          className="text-lg font-bold text-text"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Set up local transcription
        </h2>
        {!running && (
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text transition-colors cursor-pointer p-0.5"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      <p className="text-sm text-text-secondary mb-4">
        Runs on this computer: free, private, no API key, works offline. Pick
        the model new transcripts use — not sure? Use “Help me choose”.
      </p>

      {status.restart_needed && <RestartBanner />}

      {error && (
        <div className="rounded-md border border-red/30 bg-red/5 px-3 py-2 mb-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-red font-mono break-words">
                {error.length > 500 ? error.slice(0, 500) + "…" : error}
              </p>
              {error.length > 500 && (
                <details className="mt-2">
                  <summary className="text-[10px] font-mono text-red/70 cursor-pointer">
                    show full error
                  </summary>
                  <pre className="mt-2 text-[10px] font-mono text-red/80 whitespace-pre-wrap break-words">
                    {error}
                  </pre>
                </details>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="mb-5">
        <LocalModelPicker
          models={status.models}
          featured={status.featured}
          languageAnswers={status.language_answers}
          caption={status.benchmark_caption}
          selected={selected}
          onSelect={setSelected}
          disabled={running}
          onRecommendation={(r) => {
            setRec(r);
            setSelected(r.primary); // "nothing fits" clears it: no download offered
          }}
          onSetLanguage={async (code) => {
            await updateConfig({ language: code });
          }}
        />
      </div>

      {running && (
        <div className="rounded-md border border-border-subtle bg-surface-raised px-3 py-2 mb-4">
          {status.setup_progress && status.setup_progress.total > 0 ? (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-xs text-text font-mono">
                  Downloading model weights…
                </p>
                <p className="text-[11px] text-text-muted font-mono">
                  {status.setup_progress.percent ?? 0}% ·{" "}
                  {Math.round(status.setup_progress.downloaded / MB)} MB /{" "}
                  {Math.round(status.setup_progress.total / MB)} MB
                </p>
              </div>
              <div className="h-1.5 w-full rounded-full bg-border-subtle overflow-hidden">
                <div
                  className="h-full rounded-full bg-amber transition-all duration-300"
                  style={{ width: `${status.setup_progress.percent ?? 0}%` }}
                />
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-amber" />
              <p className="text-xs text-text font-mono">{describePhase(phase)}</p>
            </div>
          )}
        </div>
      )}

      {(running || logLines.length > 0) && (
        <div className="mb-4">
          <button
            onClick={() => setLogOpen(!logOpen)}
            className="flex items-center gap-1 text-xs font-mono text-text-muted hover:text-text transition-colors cursor-pointer"
          >
            {logOpen ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
            Show install log{" "}
            {logLines.length > 0 && (
              <span className="text-[10px] text-text-muted">
                ({logLines.length} lines)
              </span>
            )}
          </button>
          {logOpen && (
            <pre className="mt-2 max-h-56 overflow-auto rounded-md border border-border-subtle bg-black/20 p-2 text-[10px] font-mono text-text-muted whitespace-pre-wrap break-all">
              {logLines.length > 0 ? logLines.join("\n") : "(no output yet)"}
            </pre>
          )}
        </div>
      )}

      <div className="flex items-center justify-end gap-2">
        {!running && (
          <button
            onClick={onClose}
            className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer"
          >
            Cancel
          </button>
        )}
        <button
          onClick={handleDownload}
          disabled={starting || running || !selected}
          className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
        >
          {starting || running ? (
            <>
              <Loader2 className="w-3 h-3 animate-spin" />
              Setting up…
            </>
          ) : (
            <>
              <Check className="w-3 h-3" />
              {selectedSpec
                ? downloadMb > 0
                  ? `Download ${names} (${formatMB(downloadMb)}) & set up`
                  : `Set up ${names}`
                : "Download & set up"}
            </>
          )}
        </button>
      </div>
    </Modal>
  );
}

function describePhase(phase: string | null): string {
  switch (phase) {
    case null:
    case "starting":
      return "Starting setup…";
    case "detecting_install_method":
      return "Detecting install method…";
    case "installing_package":
      return "Installing the local engines, faster-whisper and onnx-asr (this can take a minute)…";
    case "package_installed":
      return "Engines installed. Preparing to download the model…";
    case "downloading_model":
      return "Downloading model weights from HuggingFace…";
    case "model_downloaded":
      return "Model downloaded. Finishing up…";
    case "done":
      return "Done.";
    default:
      return phase;
  }
}
