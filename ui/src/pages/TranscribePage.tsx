import { useState, useEffect, useEffectEvent } from "react";
import { Link, useOutletContext } from "react-router-dom";
import type { LayoutContext } from "../components/Layout";
import { desktop, isDoomed, useEngineStatus } from "../desktop";
import { useJob } from "../hooks/useJob";
import { getConfig, getProviders } from "../api/client";
import type { Config, Provider } from "../api/types";
import URLInput from "../components/URLInput";
import ProgressTracker from "../components/ProgressTracker";
import ResultCard from "../components/ResultCard";
import LanguageInput from "../components/LanguageInput";
import ModelInput from "../components/ModelInput";
import { defaultModelFor } from "../api/models";
import { transcriptSlug } from "../transcript";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useLocalModelNames } from "../hooks/useLocalModelNames";

// User-facing label for the diarize/diarized output format. The wire value
// stays "diarized" so the API contract doesn't change.
const formatLabel = (fmt: string) => (fmt === "diarized" ? "with-speaker-labels" : fmt);

/** What actually runs, plus any swap the backend made (keyless tier, whisper-1). */
function PlanNotes({
  plan,
}: {
  plan: { provider: string; model: string | null; notes: string[] } | null;
}) {
  const modelName = useLocalModelNames();
  if (!plan) return null;
  return (
    <div className="mt-4 self-start text-xs font-mono space-y-0.5">
      <p className="text-text-muted">
        {plan.provider}
        {plan.model ? ` · ${plan.provider === "local" ? modelName(plan.model) : plan.model}` : ""}
      </p>
      {plan.notes.map((n) => (
        <p
          key={n}
          className={`whitespace-pre-line ${n.startsWith("WARNING") ? "text-amber" : "text-text-muted/70"}`}
        >
          {n}
        </p>
      ))}
    </div>
  );
}

export default function TranscribePage() {
  const { phase, events, result, error, plan, submit, cancel, reset } = useJob();
  const [config, setConfig] = useState<Config | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [showOptions, setShowOptions] = useState(false);
  const [lastUrl, setLastUrl] = useState(""); // retained for retry / re-transcribe

  // Override fields
  const [quality, setQuality] = useState("balanced");
  // Sent only when picked on this page; otherwise the server uses the saved
  // config (the wizard may have changed it after this page loaded).
  const [qualityPicked, setQualityPicked] = useState(false);
  const [provider, setProvider] = useState(""); // "" = auto (resolved from quality)
  const [model, setModel] = useState(""); // per-run model override; only when provider is explicit
  const [language, setLanguage] = useState("");
  const [diarize, setDiarize] = useState(false);
  const [keepMedia, setKeepMedia] = useState(false);
  const [outputFormat, setOutputFormat] = useState("clean");
  const { incoming, doneIncoming, setWatching } = useOutletContext<LayoutContext>();

  useEffect(() => {
    Promise.all([getConfig(), getProviders()]).then(([c, p]) => {
      setConfig(c);
      setProviders(p);
      setQuality(c.quality || "balanced");
      setProvider(""); // default to auto — quality drives the provider
      setLanguage(c.language);
      setDiarize(c.diarize);
      setKeepMedia(c.keep_media);
      setOutputFormat(c.output_format);
    });
  }, []);

  // undefined while provider is "" (auto) → no model control, no model sent.
  const selectedProvider = providers.find((p) => p.name === provider);

  const handleSubmit = (url: string, force = false) => {
    if (!config) return Promise.resolve(false); // the input is disabled until config has loaded
    setLastUrl(url);
    // Quality only when picked here; provider only when overridden from "auto".
    return submit({
      url,
      quality: qualityPicked ? quality : undefined,
      provider: provider || undefined,
      // Model only travels with an explicit provider — on auto it's ambiguous.
      model: provider && model ? model : undefined,
      language,
      diarize,
      keep_media: keepMedia,
      output_format: outputFormat,
      force,
    });
  };

  // Extract title from download step completion event
  const downloadedTitle = events
    .filter((e) => e.step === "download" && e.status === "completed")
    .map((e) => e.message.replace(/^(Downloaded|Ready): /, ""))[0];

  // Mac app: tell the engine banner which job this page follows.
  useEffect(() => {
    setWatching(phase === "running" ? downloadedTitle || lastUrl : null);
  }, [setWatching, phase, downloadedTitle, lastUrl]);

  // Mac app: a dropped or opened file starts only while the engine reads running and the page is
  // idle or done. It leaves the stored queue only once the engine accepted it; on a failure it
  // stays at the head, and the error screen is the pause (Try again resubmits it, New drops it).
  const engine = useEngineStatus();
  // a doomed page (it saw the engine leave running; the app will reload it) starts nothing (H1)
  const engineUp = !desktop || (engine?.state === "running" && !isDoomed());
  const next = incoming[0];
  const startIncoming = useEffectEvent((path: string) => {
    // with the options set on this page right now
    void handleSubmit(path).then((ok) => ok && doneIncoming(path));
  });
  // the head is not "next" while it is being handed over or its error is on screen
  const waiting = (phase === "running" || phase === "error") && incoming[0] === lastUrl ? incoming.slice(1) : incoming;
  // H2: files that wait for the engine are named in the idle, completed and cancelled views
  const names = (list: string[]) => list.map((p) => p.split(/[\\/]/).pop()).join(", ");
  // while the engine is down every Up next line says so, whatever view it sits in (H2, K3)
  const onceUp = (n: number) => `${n === 1 ? "It starts" : "They start in turn"} once anyscribe's engine is running again.`;
  // a failed dropped file stays at the head and is tried again first (E1)
  const afterHead = (n: number) =>
    `${n === 1 ? "It starts" : "They start in turn"} after ${names(incoming.slice(0, 1))}, which is tried again once anyscribe's engine is running again.`;
  const waitingForEngine =
    !engineUp && incoming.length > 0 ? (
      <p className="mt-4 text-xs text-text-muted break-words">
        Up next: {names(incoming)}. {onceUp(incoming.length)}
      </p>
    ) : null;
  useEffect(() => {
    if (!next || !config || phase === "running" || phase === "error" || !engineUp) return;
    const id = window.setTimeout(() => startIncoming(next), 0);
    return () => window.clearTimeout(id);
  }, [next, config, phase, engineUp]);

  return (
    <div className="flex flex-col items-center justify-center min-h-full px-8 py-16">
      {phase === "idle" && (
        <div className="w-full max-w-2xl animate-fade-in">
          {/* Hero */}
          <h1
            className="text-3xl font-bold tracking-tight mb-2 text-text"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Transcribe
          </h1>
          <p className="text-text-secondary text-sm mb-8">
            Paste a YouTube, Instagram, or local file URL to transcribe.
          </p>

          <URLInput onSubmit={handleSubmit} disabled={!config} />
          {waitingForEngine}

          {/* Options accordion */}
          {config && (
            <div className="mt-6 w-full max-w-2xl">
              <button
                onClick={() => setShowOptions(!showOptions)}
                className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors cursor-pointer"
              >
                {showOptions ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
                <span className="font-mono">
                  {quality}{provider ? ` · ${provider}` : ""}{provider && model ? ` · ${model}` : ""} · {language} · {formatLabel(outputFormat)}{diarize && outputFormat !== "diarized" ? " + speakers" : ""}
                </span>
              </button>

              {showOptions && (
                <div className="mt-3 rounded-lg border border-border-subtle bg-surface p-4 space-y-3 animate-slide-up">
                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-32 shrink-0">Quality</label>
                    <div className="flex rounded-md border border-border overflow-hidden">
                      {["accuracy", "balanced", "cost", "free"].map((q) => (
                        <button
                          key={q}
                          onClick={() => {
                            setQuality(q);
                            setQualityPicked(true);
                          }}
                          className={`px-3 py-1.5 text-xs font-mono transition-colors cursor-pointer ${
                            quality === q
                              ? "bg-amber/15 text-amber border-r border-border"
                              : "bg-surface-raised text-text-muted hover:text-text border-r border-border"
                          }`}
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-32 shrink-0">Provider</label>
                    <select
                      value={provider}
                      onChange={(e) => {
                        const name = e.target.value;
                        setProvider(name);
                        setModel(
                          defaultModelFor(
                            providers.find((p) => p.name === name),
                            config.provider_models
                          )
                        );
                      }}
                      className="flex-1 bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40"
                    >
                      <option value="">auto · from quality</option>
                      {providers.map((p) => (
                        <option key={p.name} value={p.name} disabled={!p.has_key}>
                          {p.name}{p.has_key ? "" : " · needs key"}
                        </option>
                      ))}
                    </select>
                  </div>

                  {provider && provider !== "local" && (
                    <div className="flex items-center gap-4">
                      <label className="text-xs text-text-muted w-32 shrink-0">Model</label>
                      <ModelInput
                        provider={selectedProvider}
                        value={model}
                        onChange={setModel}
                      />
                    </div>
                  )}

                  {(() => {
                    const missing = providers.filter((p) => !p.has_key).length;
                    if (missing === 0) return null;
                    return (
                      <div className="flex items-center gap-4">
                        <span className="w-32 shrink-0" />
                        <p className="text-xs text-text-muted">
                          {missing} {missing === 1 ? "provider needs" : "providers need"} a key —{" "}
                          <Link to="/settings#api-keys" className="text-amber hover:underline">
                            Settings
                          </Link>
                        </p>
                      </div>
                    );
                  })()}

                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-32 shrink-0">Language</label>
                    <LanguageInput
                      provider={provider}
                      value={language}
                      onChange={setLanguage}
                    />
                  </div>

                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-32 shrink-0">Format</label>
                    <div className="flex rounded-md border border-border overflow-hidden">
                      {["clean", "timestamped", "diarized"].map((fmt) => (
                        <button
                          key={fmt}
                          onClick={() => {
                            setOutputFormat(fmt);
                            if (fmt === "diarized") setDiarize(true);
                          }}
                          className={`px-3 py-1.5 text-xs font-mono transition-colors cursor-pointer ${
                            outputFormat === fmt
                              ? "bg-amber/15 text-amber border-r border-border"
                              : "bg-surface-raised text-text-muted hover:text-text border-r border-border"
                          }`}
                        >
                          {formatLabel(fmt)}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-32 shrink-0">Multi-speaker</label>
                    <button
                      onClick={() => setDiarize(!diarize)}
                      className={`w-9 h-5 rounded-full transition-colors cursor-pointer ${
                        diarize ? "bg-amber" : "bg-border"
                      }`}
                    >
                      <div
                        className={`w-3.5 h-3.5 rounded-full bg-white transition-transform mx-0.5 ${
                          diarize ? "translate-x-4" : "translate-x-0"
                        }`}
                      />
                    </button>
                  </div>

                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-32 shrink-0">Keep media</label>
                    <button
                      onClick={() => setKeepMedia(!keepMedia)}
                      className={`w-9 h-5 rounded-full transition-colors cursor-pointer ${
                        keepMedia ? "bg-amber" : "bg-border"
                      }`}
                    >
                      <div
                        className={`w-3.5 h-3.5 rounded-full bg-white transition-transform mx-0.5 ${
                          keepMedia ? "translate-x-4" : "translate-x-0"
                        }`}
                      />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {phase === "running" && (
        <div className="w-full max-w-2xl flex flex-col items-center">
          <ProgressTracker events={events} title={downloadedTitle} />
          <PlanNotes plan={plan} />
          {waiting.length > 0 && (
            <p className="mt-4 self-start text-xs text-text-muted break-words">
              Up next: {names(waiting)}.{" "}
              {engineUp ? `${waiting.length === 1 ? "It starts" : "They start in turn"} when this one finishes.` : onceUp(waiting.length)}
            </p>
          )}
          <button
            onClick={cancel}
            className="
              mt-6 self-start
              flex items-center justify-center gap-2
              rounded-lg border border-border hover:border-red/40
              bg-surface-raised hover:bg-red/5
              px-4 py-2 text-sm text-text-secondary hover:text-red
              transition-colors cursor-pointer
            "
          >
            Stop
          </button>
        </div>
      )}

      {phase === "completed" && result && result.cached && (
        <div className="w-full max-w-2xl animate-slide-up">
          <div className="rounded-lg border border-amber/30 bg-amber/5 px-4 py-3 mb-4">
            <p className="text-sm text-amber font-medium mb-1">Already transcribed</p>
            <p className="text-xs text-text-secondary mb-2">
              This source is already in your vault.
            </p>
            <Link
              to={`/history/${transcriptSlug(result.file_path)}`}
              className="text-xs text-amber hover:underline font-mono break-all"
            >
              {result.file_path}
            </Link>
          </div>
          {waitingForEngine}
          <div className="flex gap-2">
            <button
              onClick={() => handleSubmit(lastUrl, true)}
              className="
                flex-1 flex items-center justify-center gap-2
                rounded-lg bg-amber/90 hover:bg-amber px-5 py-2.5
                text-sm font-semibold text-bg transition-colors cursor-pointer
              "
            >
              Re-transcribe
            </button>
            <button
              onClick={reset}
              className="
                flex items-center justify-center gap-2
                rounded-lg border border-border hover:border-border/80
                bg-surface-raised hover:bg-surface-hover
                px-5 py-2.5 text-sm text-text-secondary hover:text-text
                transition-colors cursor-pointer
              "
            >
              Done
            </button>
          </div>
        </div>
      )}

      {phase === "completed" && result && !result.cached && (
        <div className="w-full max-w-2xl flex flex-col items-center">
          <ResultCard result={result} onReset={reset} />
          {waitingForEngine}
          <PlanNotes plan={plan} />
        </div>
      )}

      {phase === "cancelled" && (
        <div className="w-full max-w-2xl animate-slide-up">
          <div className="rounded-lg border border-border bg-surface px-4 py-3 mb-4">
            <p className="text-sm text-text font-medium mb-1">Transcription cancelled</p>
            <p className="text-xs text-text-secondary">You stopped this job.</p>
          </div>
          {waitingForEngine}
          <div className="flex gap-2">
            <button
              onClick={() => handleSubmit(lastUrl)}
              className="
                flex-1 flex items-center justify-center gap-2
                rounded-lg bg-amber/90 hover:bg-amber px-5 py-2.5
                text-sm font-semibold text-bg transition-colors cursor-pointer
              "
            >
              Try again
            </button>
            <button
              onClick={reset}
              className="
                flex items-center justify-center gap-2
                rounded-lg border border-border hover:border-border/80
                bg-surface-raised hover:bg-surface-hover
                px-5 py-2.5 text-sm text-text-secondary hover:text-text
                transition-colors cursor-pointer
              "
            >
              New
            </button>
          </div>
        </div>
      )}

      {phase === "error" && (
        <div className="w-full max-w-2xl animate-slide-up">
          <div className="rounded-lg border border-red/30 bg-red/5 px-4 py-3 mb-4">
            <p className="text-sm text-red font-medium mb-1">Transcription failed</p>
            <p className="text-xs text-text-secondary font-mono whitespace-pre-line">{error}</p>
          </div>
          {waiting.length > 0 && (
            <p className="mb-4 text-xs text-text-muted break-words">
              Up next: {names(waiting)}.{" "}
              {engineUp
                ? `${waiting.length === 1 ? "It waits" : "They wait"} until you try this one again or choose New.`
                : incoming[0] === lastUrl ? afterHead(waiting.length) : onceUp(waiting.length)}
            </p>
          )}
          <div className="flex gap-2">
            <button
              onClick={() => lastUrl && void handleSubmit(lastUrl).then((ok) => ok && doneIncoming(lastUrl))}
              className="
                flex-1 flex items-center justify-center gap-2
                rounded-lg bg-amber/90 hover:bg-amber px-5 py-2.5
                text-sm font-semibold text-bg transition-colors cursor-pointer
              "
            >
              Try again
            </button>
            <button
              onClick={() => {
                doneIncoming(lastUrl); // drops a waiting file only when it is the one that failed
                reset();
              }}
              className="
                flex items-center justify-center gap-2
                rounded-lg border border-border hover:border-border/80
                bg-surface-raised hover:bg-surface-hover
                px-5 py-2.5 text-sm text-text-secondary hover:text-text
                transition-colors cursor-pointer
              "
            >
              New
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
