/** Small status blocks shared by the local-setup surfaces (first-run wizard,
 * setup modal, Settings). */

import { useEffect, useState } from "react";
import { AlertCircle, Check, Loader2, RotateCcw } from "lucide-react";
import { listLocalModels } from "../api/client";
import type { LocalModelEntry } from "../api/types";
import { formatMB } from "../api/models";

/** Setup replaced an engine the running server had already loaded.
 * ``children`` adds a sentence after the banner's own (the wizard's way back). */
export function RestartBanner({ children }: { children?: React.ReactNode }) {
  return (
    <div
      role="alert"
      className="rounded-md border border-amber/40 bg-amber/[0.08] px-3 py-2.5 mb-4 flex items-start gap-2"
    >
      <RotateCcw className="w-4 h-4 text-amber mt-0.5 shrink-0" />
      <p className="text-xs text-text">
        <b>Restart anyscribe to finish setting up local transcription.</b> Stop
        anyscribe and start it again: in the terminal where <code>anyscribe ui</code>{" "}
        runs, press Ctrl+C, then run <code>anyscribe ui</code>. Using the app icon?
        Quit anyscribe from its menu-bar or tray icon, then open it again. Until then,
        local transcription may fail to open audio files.{children && <> {children}</>}
      </p>
    </div>
  );
}

/** Live state of the extra models setup downloads afterwards (Turbo for a
 * mix): downloading with progress, ready, or failed with the reason. The
 * ``pendingNote`` shows only while one is still downloading; a failure says
 * what won't work until it is downloaded. */
export function ExtraDownloads({
  ids,
  name: nameOf,
  pendingNote,
}: {
  ids: string[];
  name: (id: string) => string;
  pendingNote: string;
}) {
  const [models, setModels] = useState<LocalModelEntry[]>([]);
  const failed = (m?: LocalModelEntry) =>
    !!m && !m.runnable && !!m.last_error && !m.downloading && !m.queued;
  const settled = (m?: LocalModelEntry) => !!m && (m.runnable || failed(m));
  const done = models.length > 0 && ids.every((id) => settled(models.find((m) => m.size === id)));
  const failedIds = ids.filter((id) => failed(models.find((m) => m.size === id)));

  useEffect(() => {
    if (ids.length === 0 || done) return;
    let stop = false;
    const tick = async () => {
      try {
        const r = await listLocalModels();
        if (!stop) setModels(r.models);
      } catch {
        // transient
      }
    };
    void tick();
    const id = setInterval(tick, 1500);
    return () => {
      stop = true;
      clearInterval(id);
    };
  }, [ids, done]);

  if (ids.length === 0) return null;
  return (
    <div className="space-y-1.5" data-testid="extra-downloads">
      {ids.map((id) => {
        const m = models.find((x) => x.size === id);
        const name = m?.spec.display_name ?? nameOf(id);
        const err = failed(m) ? m?.last_error : null;
        return (
          <div key={id} className="flex items-center justify-between gap-3 text-xs font-mono">
            <span className="text-text-muted">{name}</span>
            {err ? (
              <span className="text-red flex items-center gap-1 text-right">
                <AlertCircle className="w-3 h-3 shrink-0" /> download failed: {err}
              </span>
            ) : m?.runnable ? (
              <span className="text-green flex items-center gap-1">
                <Check className="w-3 h-3" /> ready
              </span>
            ) : (
              <span className="text-amber flex items-center gap-1" role="status">
                <Loader2 className="w-3 h-3 animate-spin" />
                {m?.progress && m.progress.total > 0
                  ? `downloading ${m.progress.percent ?? 0}%`
                  : m?.queued
                    ? "waiting to download"
                    : `downloading${m ? ` (${formatMB(m.spec.download_mb)})` : ""}`}
              </span>
            )}
          </div>
        );
      })}
      {!done && <p className="text-[11px] text-text-muted mt-1.5">{pendingNote}</p>}
      {failedIds.length > 0 && (
        <p className="text-[11px] text-red mt-1.5">
          Hindi and other languages won't work until you download{" "}
          {failedIds.map((id) => models.find((m) => m.size === id)?.spec.display_name ?? nameOf(id)).join(" + ")}{" "}
          in Settings.
        </p>
      )}
    </div>
  );
}
