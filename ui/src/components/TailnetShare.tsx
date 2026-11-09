/** A tailnet link that opens on click/tap, with a copy button beside it. */

import { useState } from "react";
import { Check, Copy } from "lucide-react";

export function TailnetLink({ url, compact = false }: { url: string; compact?: boolean }) {
  const [copied, setCopied] = useState<"yes" | "failed" | null>(null);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied("yes");
    } catch {
      setCopied("failed"); // no clipboard access: the link text is still selectable
    }
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="flex items-center gap-1.5 min-w-0">
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        title={url}
        className={`font-mono text-amber hover:underline ${compact ? "text-[11px] break-all" : "text-xs truncate"}`}
      >
        {compact ? url.replace(/^https:\/\//, "").replace(/\/$/, "") : url}
      </a>
      <button
        type="button"
        onClick={() => void copy()}
        aria-label="Copy link"
        className="shrink-0 flex items-center gap-1 rounded px-1.5 py-1 text-text-muted hover:text-text hover:bg-surface-hover transition-colors cursor-pointer"
      >
        {copied === "yes" ? (
          <Check className="w-3 h-3 text-green" />
        ) : (
          <Copy className="w-3 h-3" />
        )}
        {!compact && (
          <span className="text-xs">
            {copied === "yes" ? "Copied" : copied === "failed" ? "Copy failed" : "Copy"}
          </span>
        )}
      </button>
    </div>
  );
}
