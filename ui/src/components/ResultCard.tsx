import { BookOpen, Check, Copy, FileText, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { transcriptSlug } from "../transcript";
import type { JobResult } from "../api/types";
import { useLocalModelNames } from "../hooks/useLocalModelNames";

interface ResultCardProps {
  result: JobResult;
  onReset: () => void;
}

export default function ResultCard({ result, onReset }: ResultCardProps) {
  const [copied, setCopied] = useState(false);
  const modelName = useLocalModelNames();

  const handleCopy = async () => {
    await navigator.clipboard.writeText(result.file_path);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const stats = [
    { label: "Duration", value: result.duration || "—" },
    { label: "Language", value: result.language },
    { label: "Words", value: result.word_count.toLocaleString() },
    {
      label: "Provider",
      value: result.model
        ? `${result.provider} · ${result.provider === "local" ? modelName(result.model) : result.model}`
        : result.provider,
    },
  ];

  return (
    <div className="w-full max-w-2xl animate-slide-up">
      {/* Success header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-6 h-6 rounded-full bg-green/15 flex items-center justify-center">
          <Check className="w-3.5 h-3.5 text-green" />
        </div>
        <span
          className="text-lg font-semibold text-text tracking-tight"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Done
        </span>
      </div>

      {/* Title */}
      <p className="text-sm text-text-secondary mb-5 truncate">
        {result.title}
      </p>

      {/* Run-time switches (e.g. the language check sent Hindi to Whisper):
          never silent, so they lead the card. */}
      {(result.notes ?? []).map((n) => (
        <p
          key={n}
          role="note"
          className="mb-4 text-[13px] text-text-secondary border-l-[3px] border-blue bg-blue/[0.07] rounded-md px-3 py-2.5"
        >
          {n}
        </p>
      ))}

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {stats.map(({ label, value }) => (
          <div
            key={label}
            className="rounded-lg bg-surface border border-border-subtle px-3 py-2.5"
          >
            <div className="text-[11px] text-text-muted uppercase tracking-wider mb-1">
              {label}
            </div>
            <div className="text-sm font-mono text-text font-medium">
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* File path */}
      <div className="flex items-center gap-2 rounded-lg bg-surface border border-border-subtle px-3 py-2.5 mb-5">
        <FileText className="w-3.5 h-3.5 text-text-muted shrink-0" />
        <code className="text-xs text-text-secondary truncate flex-1 font-mono">
          {result.file_path}
        </code>
        <button
          onClick={handleCopy}
          className="text-text-muted hover:text-text transition-colors shrink-0 cursor-pointer"
        >
          {copied ? (
            <Check className="w-3.5 h-3.5 text-green" />
          ) : (
            <Copy className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      {/* Actions: reading it is the main one */}
      <div className="flex flex-col sm:flex-row gap-2">
        <Link
          to={`/history/${transcriptSlug(result.file_path)}`}
          className="
            flex-1 flex items-center justify-center gap-2
            rounded-lg bg-amber/90 hover:bg-amber px-5 py-2.5
            text-sm font-semibold text-bg transition-colors
          "
        >
          <BookOpen className="w-4 h-4" />
          Read transcript
        </Link>
        <button
          onClick={onReset}
          className="
            flex items-center justify-center gap-2
            rounded-lg border border-border hover:border-border/80
            bg-surface-raised hover:bg-surface-hover
            px-5 py-2.5 text-sm text-text-secondary hover:text-text
            transition-colors cursor-pointer
          "
        >
          <Plus className="w-4 h-4" />
          New transcription
        </button>
      </div>
    </div>
  );
}
