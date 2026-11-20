/** ffmpeg install command (shared with SetupBanner) and the setup wizard's
 * "ffmpeg missing" notice. */

import { useState } from "react";
import { AlertTriangle, Check, Copy, Loader2, Terminal } from "lucide-react";

function detectPlatform(): "macos" | "windows" | "linux" {
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes("mac")) return "macos";
  if (ua.includes("win")) return "windows";
  return "linux";
}

const FFMPEG_COMMANDS: Record<string, { cmd: string; note?: string }> = {
  macos: { cmd: "brew install ffmpeg" },
  windows: { cmd: "winget install Gyan.FFmpeg" },
  linux: { cmd: "sudo apt install ffmpeg", note: "or your distro's package manager" },
};

/** The install command for this computer, with a copy button. */
export function FfmpegCommand() {
  const [copied, setCopied] = useState(false);
  const info = FFMPEG_COMMANDS[detectPlatform()];

  const handleCopy = () => {
    navigator.clipboard.writeText(info.cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-2">
      <div className="flex items-center gap-1.5 bg-surface-raised border border-border rounded-md px-2.5 py-1">
        <Terminal className="w-3 h-3 text-text-muted" />
        <code className="text-xs font-mono text-text">{info.cmd}</code>
      </div>
      <button
        onClick={handleCopy}
        className="text-text-muted hover:text-text transition-colors cursor-pointer p-1"
        title="Copy command"
        aria-label="Copy command"
      >
        {copied ? <Check className="w-3 h-3 text-green" /> : <Copy className="w-3 h-3" />}
      </button>
      {info.note && <span className="text-xs text-text-muted">{info.note}</span>}
    </div>
  );
}

/** "One more thing: ffmpeg". ``onCheckAgain`` re-reads the server's status and
 * resolves true once ffmpeg is found. */
export function FfmpegNotice({ onCheckAgain }: { onCheckAgain: () => Promise<boolean> }) {
  const [checking, setChecking] = useState(false);
  const [stillMissing, setStillMissing] = useState(false);

  const check = async () => {
    setChecking(true);
    try {
      setStillMissing(!(await onCheckAgain()));
    } catch {
      setStillMissing(true);
    } finally {
      setChecking(false);
    }
  };

  return (
    <div role="alert" className="rounded-lg border border-amber/30 bg-amber/5 px-4 py-3 my-3">
      <p className="flex items-center gap-2 text-sm font-medium text-text">
        <AlertTriangle className="w-4 h-4 text-amber shrink-0" />
        One more thing: ffmpeg
      </p>
      <p className="text-xs text-text-secondary mt-1.5">
        anyscribe needs ffmpeg, a free audio tool, to read audio and video. Install it with the
        command below, then click Check again.
      </p>
      <FfmpegCommand />
      {detectPlatform() === "windows" && (
        <p className="text-xs text-text-secondary mt-2">
          If it still isn't found after installing, quit anyscribe from the tray and open it again.
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          onClick={check}
          disabled={checking}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
        >
          {checking && <Loader2 className="w-3 h-3 animate-spin" />}
          Check again
        </button>
        {stillMissing && !checking && (
          <span className="text-xs text-text-muted">Still not found.</span>
        )}
      </div>
    </div>
  );
}
