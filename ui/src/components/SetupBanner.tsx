/** Setup banner — shown on all pages when ffmpeg or provider keys are missing. */

import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Check, Circle, X } from "lucide-react";
import { getHealth, getKeysStatus } from "../api/client";
import { FfmpegCommand } from "./FfmpegNotice";

const POLL_INTERVAL_MS = 30_000;

export default function SetupBanner() {
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState(false);
  const [ffmpegOk, setFfmpegOk] = useState(true);
  const [hasAnyKey, setHasAnyKey] = useState(true);

  const checkSetup = useCallback(async () => {
    try {
      const [health, keys] = await Promise.all([getHealth(), getKeysStatus()]);
      setFfmpegOk(health.dependencies.ffmpeg && health.dependencies.ffprobe);
      setHasAnyKey(Object.values(keys).some(Boolean));
    } catch {
      // Backend not reachable — don't show banner
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const id = window.setTimeout(() => {
      void checkSetup();
    }, 0);
    return () => window.clearTimeout(id);
  }, [checkSetup]);

  // Poll while banner is visible
  useEffect(() => {
    if (loading || dismissed || (ffmpegOk && hasAnyKey)) return;
    const id = setInterval(checkSetup, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [loading, dismissed, ffmpegOk, hasAnyKey, checkSetup]);

  // Don't render if setup is complete, loading, or dismissed
  if (loading || dismissed || (ffmpegOk && hasAnyKey)) return null;

  return (
    <div className="mx-6 mt-6 rounded-lg border border-amber/30 bg-amber/5 px-5 py-4 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber" />
          <span className="text-sm font-medium text-text">
            Setup needed to start transcribing
          </span>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-text-muted hover:text-text transition-colors cursor-pointer p-0.5"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {/* Step 1: ffmpeg */}
        <div className="flex items-start gap-2.5">
          {ffmpegOk ? (
            <Check className="w-4 h-4 text-green mt-0.5 shrink-0" />
          ) : (
            <Circle className="w-4 h-4 text-amber mt-0.5 shrink-0" />
          )}
          <div className="flex-1 min-w-0">
            <p className={`text-sm ${ffmpegOk ? "text-text-muted line-through" : "text-text"}`}>
              Install ffmpeg
            </p>
            {!ffmpegOk && <FfmpegCommand />}
          </div>
        </div>

        {/* Step 2: Provider key */}
        <div className="flex items-start gap-2.5">
          {hasAnyKey ? (
            <Check className="w-4 h-4 text-green mt-0.5 shrink-0" />
          ) : (
            <Circle className="w-4 h-4 text-amber mt-0.5 shrink-0" />
          )}
          <div>
            <p className={`text-sm ${hasAnyKey ? "text-text-muted line-through" : "text-text"}`}>
              Set up a transcription provider
            </p>
            {!hasAnyKey && (
              <p className="text-xs text-text-muted mt-1">
                Go to{" "}
                <Link to="/settings" className="text-amber hover:underline">
                  Settings → Providers
                </Link>{" "}
                and add an API key
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
