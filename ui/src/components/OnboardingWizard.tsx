/** First-run onboarding wizard for the Web UI.
 *
 * Full-screen modal that walks the user through the minimum required to start
 * transcribing: pick a provider, hand over a key (or set up local), point at
 * a workspace, done. Advanced preferences (language default, output format,
 * Instagram, etc.) are NOT in the wizard — they default to sane values and
 * users tweak them in Settings later.
 *
 * The wizard writes to the backend exactly once, at the final Done step,
 * calling ``POST /api/onboarding/save`` which fans out to config + keys. The
 * one exception is offline opt-in: if the user says yes to local, that step
 * kicks off ``POST /api/local/setup`` inline and polls until the download
 * finishes — because that work can take minutes and shouldn't block the final
 * Done click.
 *
 * Trigger: App.tsx mounts this whenever ``GET /api/onboarding/status`` reports
 * ``completed: false`` AND localStorage flag ``scribe_onboarding_dismissed``
 * isn't set. Settings has a button to re-open it manually.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Loader2, AlertCircle, ChevronRight, ChevronLeft, Sparkles, X } from "lucide-react";
import Modal from "./Modal";
import {
  getOnboardingStatus,
  saveOnboarding,
  testProvider,
  setupLocal,
  getLocalStatus,
  getSetupLog,
  getLocalRegistry,
} from "../api/client";
import type {
  LocalRecommendation,
  LocalRegistry,
  LocalStatusResponse,
  ProviderTestResult,
} from "../api/types";
import LocalModelPicker from "./LocalModelPicker";
import { ExtraDownloads, RestartBanner } from "./LocalSetupNotes";
import { FfmpegNotice } from "./FfmpegNotice";
import { downloadMbFor, formatMB, formatPerHour } from "../api/models";
import { useLocalModelNames } from "../hooks/useLocalModelNames";

// Keep these in lock-step with backend ``onboard_headless.PROVIDER_KEY_ENV``.
const API_PROVIDERS = [
  { name: "openai", label: "OpenAI Whisper", description: "General purpose, multilingual, segment timestamps", env: "OPENAI_API_KEY", url: "https://platform.openai.com/api-keys" },
  { name: "deepgram", label: "Deepgram", description: "Fast, accurate, native diarization + Hindi Latin", env: "DEEPGRAM_API_KEY", url: "https://console.deepgram.com/" },
  { name: "groq", label: "Groq", description: "Cheapest + fastest cloud Whisper (large-v3-turbo)", env: "GROQ_API_KEY", url: "https://console.groq.com/keys" },
  { name: "elevenlabs", label: "ElevenLabs Scribe", description: "High accuracy, 99 languages, word-level timestamps", env: "ELEVENLABS_API_KEY", url: "https://elevenlabs.io/app/settings/api-keys" },
  { name: "sargam", label: "Sarvam AI", description: "Optimized for Indic languages", env: "SARGAM_API_KEY", url: "https://dashboard.sarvam.ai" },
  { name: "openrouter", label: "OpenRouter", description: "Access various models via unified API", env: "OPENROUTER_API_KEY", url: "https://openrouter.ai/keys" },
];

type Step =
  | "welcome"
  | "provider"
  | "api_key"
  | "offline_opt_in"
  | "workspace"
  | "done";

type FormState = {
  provider: string | null;
  apiKey: string;
  workspace: string;
  enableLocal: boolean;
  localModel: string | null;
  /** "Set my language to Hindi" from Help me choose; saved at Finish */
  language: string | null;
  /** extra models setup downloads afterwards (Turbo for a mix), from the server */
  alsoModels: string[];
  restartNeeded: boolean;
};

interface Props {
  onClose: () => void;
}

export default function OnboardingWizard({ onClose }: Props) {
  const [step, setStep] = useState<Step>("welcome");
  const [form, setForm] = useState<FormState>({
    provider: null,
    apiKey: "",
    workspace: "",
    enableLocal: false,
    localModel: null,
    language: null,
    alsoModels: [],
    restartNeeded: false,
  });
  const [saving, setSaving] = useState(false);
  // a local download is running: the wizard can't be closed or skipped
  const [localRunning, setLocalRunning] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [defaultWorkspace, setDefaultWorkspace] = useState("");
  const modelName = useLocalModelNames(); // fetched now, so All set shows names at once
  // The recommended card as the starting pick, unless a pick was made first
  // (a functional update, so a late status response can't undo a choice).
  const presetSize = useCallback(
    (s: string) => setForm((f) => (f.localModel ? f : { ...f, localModel: s })),
    []
  );

  // Preload the default workspace so StepWorkspace can show it as a hint.
  useEffect(() => {
    getOnboardingStatus()
      .then(() => {
        // The status endpoint doesn't return the default path directly; we
        // derive it from /api/config which always returns _resolved_workspace.
        return fetch("/api/config")
          .then((r) => r.json())
          .then((c) => setDefaultWorkspace(c._resolved_workspace || ""));
      })
      .catch(() => {
        // non-critical
      });
  }, []);

  // A download already running (the page was reloaded mid-download, or Settings
  // started one): open on it instead of offering Download again.
  useEffect(() => {
    getLocalStatus()
      .then((s) => {
        if (!s.setup_running) return;
        setForm((f) => ({
          ...f,
          provider: "local",
          enableLocal: true,
          localModel: s.setup_last_model,
        }));
        setStep("offline_opt_in");
      })
      .catch(() => undefined);
  }, []);

  // Dismissing (Skip for now) sets the localStorage flag so we don't pop the
  // wizard again next page load.
  const dismiss = (persist: boolean) => {
    if (persist) {
      try {
        localStorage.setItem("scribe_onboarding_dismissed", "1");
      } catch {
        // private mode / storage disabled — not fatal
      }
    }
    onClose();
  };

  const branchFromProvider = (provider: string) => {
    setForm((f) => ({ ...f, provider }));
    if (provider === "local") {
      // Local path: jump straight into model setup (no API key step). The
      // offline_opt_in step handles the size picker + setup trigger.
      setForm((f) => ({ ...f, enableLocal: true }));
      setStep("offline_opt_in");
    } else {
      setStep("api_key");
    }
  };

  const finish = async () => {
    if (!form.provider) return;
    setSaving(true);
    setSaveError(null);
    try {
      await saveOnboarding({
        provider: form.provider,
        api_key: form.provider !== "local" ? form.apiKey || undefined : undefined,
        workspace: form.workspace || undefined,
        language: form.language || undefined,
        local_model:
          form.provider === "local"
            ? form.localModel || undefined
            : undefined,
      });
      dismiss(true);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Failed to save onboarding");
    } finally {
      setSaving(false);
    }
  };

  // Count only the steps on the chosen path (the local path has no API key step).
  const path: Step[] =
    form.provider === "local"
      ? ["provider", "offline_opt_in", "workspace"]
      : ["provider", "api_key", "offline_opt_in", "workspace"];
  const stepIndex = path.indexOf(step) + 1;

  return (
    <Modal
      onClose={() => dismiss(false)}
      disableClose={saving || localRunning}
      ariaLabelledBy="onboarding-title"
      size="xl"
    >
      {/* Header: title + progress + skip */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2
            id="onboarding-title"
            className="text-lg font-bold text-text"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {stepTitle(step)}
          </h2>
          {step !== "welcome" && step !== "done" && (
            <p className="text-[10px] font-mono text-text-muted mt-0.5">
              Step {stepIndex}
              {form.provider ? ` of ${path.length}` : ""}
            </p>
          )}
        </div>
        {step !== "done" && !saving && localRunning && (
          <span className="text-xs font-mono text-text-muted text-right">
            Skip is off until the download finishes
          </span>
        )}
        {step !== "done" && !saving && !localRunning && (
          <button
            onClick={() => dismiss(true)}
            className="flex items-center gap-1 text-xs font-mono text-text-muted hover:text-text transition-colors cursor-pointer"
            aria-label="Skip onboarding"
          >
            Skip for now
            <X className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Error banner at wizard level (save failures land here) */}
      {saveError && (
        <div className="rounded-md border border-red/30 bg-red/5 px-3 py-2 mb-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red mt-0.5 shrink-0" />
            <p className="text-xs text-red font-mono break-words">{saveError}</p>
          </div>
        </div>
      )}

      {/* Step body */}
      {step === "welcome" && (
        <StepWelcome onNext={() => setStep("provider")} />
      )}
      {step === "provider" && (
        <StepProvider onPick={branchFromProvider} />
      )}
      {step === "api_key" && form.provider && form.provider !== "local" && (
        <StepApiKey
          providerName={form.provider}
          value={form.apiKey}
          onChange={(v) => setForm((f) => ({ ...f, apiKey: v }))}
          onBack={() => setStep("provider")}
          onNext={() => setStep("offline_opt_in")}
        />
      )}
      {step === "offline_opt_in" && (
        <StepOfflineOptIn
          // Local-as-primary provider: treat as "required". API-as-primary:
          // optional toggle.
          required={form.provider === "local"}
          selected={form.localModel}
          enabled={form.enableLocal}
          onSetEnabled={(e) => setForm((f) => ({ ...f, enableLocal: e }))}
          onSelectSize={(s: string | null) => setForm((f) => ({ ...f, localModel: s }))}
          onPresetSize={presetSize}
          onSetLanguage={(code) => setForm((f) => ({ ...f, language: code }))}
          onSetupDone={(done) => setForm((f) => ({ ...f, ...done }))}
          onRunning={setLocalRunning}
          onBack={() =>
            setStep(form.provider === "local" ? "provider" : "api_key")
          }
          onNext={() => setStep("workspace")}
        />
      )}
      {step === "workspace" && (
        <StepWorkspace
          defaultPath={defaultWorkspace}
          value={form.workspace}
          onChange={(v) => setForm((f) => ({ ...f, workspace: v }))}
          onBack={() => setStep("offline_opt_in")}
          onNext={() => setStep("done")}
        />
      )}
      {step === "done" && (
        <StepDone
          form={form}
          name={modelName}
          saving={saving}
          onBack={() => setStep("workspace")}
          onFinish={finish}
        />
      )}
    </Modal>
  );
}

function stepTitle(step: Step): string {
  switch (step) {
    case "welcome":
      return "Welcome to anyscribe";
    case "provider":
      return "How should anyscribe transcribe?";
    case "api_key":
      return "Add your API key";
    case "offline_opt_in":
      return "Local transcription";
    case "workspace":
      return "Workspace location";
    case "done":
      return "All set";
  }
}

// ── Step components ───────────────────────────────────────────────

function StepWelcome({ onNext }: { onNext: () => void }) {
  return (
    <>
      <p className="text-sm text-text-muted mb-6">
        anyscribe turns videos and audio into clean markdown transcripts in your
        Obsidian vault. Let's get you set up in a minute.
      </p>
      <div className="rounded-lg border border-border-subtle bg-surface-raised px-4 py-3 mb-6">
        <p className="text-xs text-text-muted">
          You can skip this any time and configure things later in Settings.
        </p>
      </div>
      <div className="flex justify-end">
        <button
          onClick={onNext}
          className="rounded-md bg-amber text-surface px-4 py-2 text-sm font-mono hover:bg-amber/80 transition-colors cursor-pointer flex items-center gap-2"
        >
          Let's go
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </>
  );
}

function StepProvider({ onPick }: { onPick: (provider: string) => void }) {
  const [cloud, setCloud] = useState(false);
  // The registry alone (no disk scan, no engine import), so this line never
  // waits on a slow status call.
  const [registry, setRegistry] = useState<LocalRegistry | null>(null);
  useEffect(() => {
    getLocalRegistry()
      .then(setRegistry)
      .catch(() => undefined);
  }, []);
  const rec = registry?.specs[registry.recommended_model];

  return (
    <>
      <p className="text-sm text-text-muted mb-4">You can change this any time in Settings.</p>
      <div className="grid gap-2.5 mb-6">
        <button
          onClick={() => onPick("local")}
          data-choice="local"
          className="w-full text-left rounded-[10px] border border-amber bg-amber/[0.06] hover:bg-amber/10 p-4 transition-colors cursor-pointer"
        >
          <span className="flex flex-wrap items-center gap-2 text-[15px] font-semibold text-text">
            <Sparkles className="w-3.5 h-3.5 text-amber" />
            On this computer
            <span className="text-[10px] font-mono font-medium px-[7px] py-[2px] rounded-[5px] bg-amber-dim text-amber">
              recommended
            </span>
          </span>
          <span className="block text-[13px] text-text-secondary mt-1">
            Free and private. No account, no API key, works offline.
            {rec && (
              <>
                {" "}
                Downloads {rec.display_name} ({formatMB(rec.download_mb)}) once. About{" "}
                {formatPerHour(rec.min_per_hour)} per hour of audio on our 6-core test desktop;
                your computer may be faster or slower.
              </>
            )}
          </span>
        </button>
        <button
          onClick={() => setCloud(!cloud)}
          aria-expanded={cloud}
          data-choice="cloud"
          className={`w-full text-left rounded-[10px] border p-4 transition-colors cursor-pointer ${
            cloud ? "border-amber bg-amber/[0.06]" : "border-border-subtle bg-surface-raised hover:bg-surface-hover"
          }`}
        >
          <span className="block text-[15px] font-semibold text-text">With a cloud service</span>
          <span className="block text-[13px] text-text-secondary mt-1">
            Slightly more accurate on hard audio, adds speaker labels, very fast. Needs an
            API key from ElevenLabs, Deepgram, OpenAI, Groq or others. Paid per minute.
          </span>
        </button>
        {cloud && (
          <div className="space-y-2 pl-3 border-l-2 border-border-subtle">
            {API_PROVIDERS.map((p) => (
              <button
                key={p.name}
                onClick={() => onPick(p.name)}
                className="w-full text-left rounded-lg border border-border-subtle bg-surface hover:border-amber/40 hover:bg-amber/5 px-4 py-3 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-mono text-text font-bold">{p.name}</span>
                  <span className="text-xs text-text-muted">· {p.label}</span>
                </div>
                <p className="text-xs text-text-muted">{p.description}</p>
              </button>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function StepApiKey({
  providerName,
  value,
  onChange,
  onBack,
  onNext,
}: {
  providerName: string;
  value: string;
  onChange: (v: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const [testing, setTesting] = useState(false);
  // The last check and the text it checked: editing the key makes it stale.
  const [check, setCheck] = useState<(ProviderTestResult & { key: string }) | null>(null);
  const testResult = check && check.key === value ? check : null;
  const provider = API_PROVIDERS.find((p) => p.name === providerName);
  // Accepted, or nothing could check it (Sarvam, provider unreachable): Next goes on.
  // A refusal or an error answer stays, with "Use this key anyway".
  const accepted = !!testResult?.success && testResult.checked !== false;
  const unchecked = testResult?.checked === false;
  const refused = !!testResult && !testResult.success && !unchecked;

  const runCheck = async (): Promise<ProviderTestResult | null> => {
    if (!value) return null;
    setTesting(true);
    let result: ProviderTestResult;
    try {
      // Pass the typed-but-unsaved key to the test endpoint so it actually
      // validates what the user just entered (rather than whatever's already
      // in .env, which may be stale or empty during wizard-phase).
      result = await testProvider(providerName, value);
    } catch (e) {
      result = {
        success: false,
        checked: false,
        message: e instanceof Error ? e.message : "Test failed",
      };
    } finally {
      setTesting(false);
    }
    setCheck({ ...result, key: value });
    return result;
  };

  const handleNext = async () => {
    if (testResult) {
      if (!refused) onNext();
      return;
    }
    const result = await runCheck();
    if (result?.success && result.checked !== false) onNext();
  };

  return (
    <>
      <p className="text-sm text-text-muted mb-4">
        Paste your {provider?.label || providerName} API key. It's stored
        locally in <code className="text-xs font-mono text-text">~/.anyscribe/.env</code> and
        never shared.
      </p>
      {providerName === "openai" && (
        <p className="text-xs text-text-secondary border-l-[3px] border-amber bg-amber/[0.07] rounded-md px-3 py-2 mb-4">
          OpenAI is prepaid: add credit to your OpenAI account first, or transcripts will fail.
        </p>
      )}
      <div className="mb-4">
        <input
          type="password"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          // a check answers for the text it sent: no edits until it does
          readOnly={testing}
          placeholder="Paste key here"
          autoFocus
          className="w-full bg-surface-raised border border-border rounded-md px-3 py-2 text-sm text-text font-mono outline-none focus:border-amber/40 read-only:opacity-60"
        />
        {provider?.url && (
          <p className="text-[10px] font-mono text-text-muted mt-2">
            Need a key?{" "}
            <a
              href={provider.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-amber hover:underline"
            >
              {provider.url.replace(/^https?:\/\//, "")}
            </a>
          </p>
        )}
      </div>

      {testResult && (
        <div
          role="status"
          className={`rounded-md px-3 py-2 mb-4 border ${
            accepted
              ? "border-green/30 bg-green/5"
              : unchecked
                ? "border-amber/30 bg-amber/5"
                : "border-red/30 bg-red/5"
          }`}
        >
          <div className="flex items-start gap-2">
            {accepted ? (
              <Check className="w-3.5 h-3.5 text-green mt-0.5 shrink-0" />
            ) : (
              <AlertCircle
                className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${unchecked ? "text-amber" : "text-red"}`}
              />
            )}
            <p
              className={`text-xs ${
                accepted ? "text-green" : unchecked ? "text-amber" : "text-red"
              }`}
            >
              {testResult.message}
            </p>
          </div>
          {refused && (
            <button
              onClick={onNext}
              disabled={testing}
              className="mt-2 ml-5.5 text-xs text-text-muted underline hover:text-text cursor-pointer"
            >
              Use this key anyway
            </button>
          )}
        </div>
      )}

      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          disabled={testing}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
        >
          <ChevronLeft className="w-3 h-3" />
          Back
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={runCheck}
            disabled={!value || testing}
            className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50"
          >
            Test key
          </button>
          <button
            onClick={handleNext}
            disabled={!value || testing || refused}
            className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
          >
            {testing ? (
              <>
                <Loader2 className="w-3 h-3 animate-spin" />
                Checking key…
              </>
            ) : (
              <>
                Next
                <ChevronRight className="w-3 h-3" />
              </>
            )}
          </button>
        </div>
      </div>
    </>
  );
}

function StepOfflineOptIn({
  required,
  enabled,
  selected,
  onSetEnabled,
  onSelectSize,
  onPresetSize,
  onSetLanguage,
  onSetupDone,
  onRunning,
  onBack,
  onNext,
}: {
  required: boolean;
  enabled: boolean;
  selected: string | null;
  onSetEnabled: (v: boolean) => void;
  onSelectSize: (s: string | null) => void;
  onPresetSize: (s: string) => void;
  onSetLanguage: (code: string) => void;
  onSetupDone: (done: Pick<FormState, "alsoModels" | "restartNeeded">) => void;
  onRunning: (running: boolean) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const [status, setStatus] = useState<LocalStatusResponse | null>(null);
  const [settingUp, setSettingUp] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);
  // setup ended with no error but still not set up (ffmpeg shows its own notice)
  const [missing, setMissing] = useState<string | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [logOpen, setLogOpen] = useState(false);
  const logCursorRef = useRef(0);
  const [rec, setRec] = useState<LocalRecommendation | null>(null);

  useEffect(() => {
    getLocalStatus().then((s) => {
      setStatus(s);
      onPresetSize(s.recommended_model);
      if (s.setup_running) setSettingUp(true); // watch the running download
    });
  }, [onPresetSize]);

  useEffect(() => {
    onRunning(settingUp);
    return () => onRunning(false);
  }, [settingUp, onRunning]);

  // Poll during setup.
  useEffect(() => {
    if (!settingUp) return;
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
          setSettingUp(false);
          if (s.setup_error) {
            setSetupError(s.setup_error);
            setLogOpen(true);
          } else if (s.set_up) {
            // The server queued the extras (Turbo for a mix) itself; All set
            // shows their progress.
            onSetupDone({ alsoModels: s.setup_also, restartNeeded: s.restart_needed });
            onNext();
          } else if (s.ffmpeg_ok) {
            setMissing(missingPart(s));
          }
        }
      } catch {
        // transient
      }
    }, 1500);
    return () => clearInterval(id);
  }, [settingUp, onNext, onSetupDone]);

  // The only way forward with local on: setup (quick when the model can
  // already run) switches the default and queues the extras server-side.
  const handleStartSetup = async () => {
    if (!selected) return;
    setSettingUp(true);
    setSetupError(null);
    setMissing(null);
    setLogLines([]);
    logCursorRef.current = 0;
    try {
      await setupLocal(selected, keptRec?.also ?? []);
      const s = await getLocalStatus();
      setStatus(s);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to start setup";
      if (msg.startsWith("409")) {
        // one is already running (another tab, or Settings): watch it instead
        const s = await getLocalStatus().catch(() => null);
        if (s?.setup_running) {
          setStatus(s);
          return;
        }
      }
      setSetupError(msg);
      setSettingUp(false);
    }
  };

  const models = status?.models || [];
  const pick = models.find((m) => m.size === selected)?.spec;
  // What the button downloads: the pick, a mix's second model, and the
  // language check for Parakeet, minus anything already on disk.
  const keptRec = rec && rec.primary === selected ? rec : null;
  const toFetch = [selected, ...(keptRec?.also ?? [])].filter(Boolean) as string[];
  const downloadMb = downloadMbFor(models, toFetch);
  const allRunnable =
    toFetch.length > 0 && toFetch.every((id) => models.find((m) => m.size === id)?.runnable);
  const names = toFetch.map((id) => models.find((m) => m.size === id)?.spec.display_name ?? id);
  const ffmpegMissing = !!status && !status.ffmpeg_ok;
  // the model the running setup fetches: may differ from the pick after a reload
  const runningName =
    models.find((m) => m.size === status?.setup_last_model)?.spec.display_name ??
    pick?.display_name;
  const checkFfmpeg = async () => {
    const s = await getLocalStatus();
    setStatus(s);
    return s.ffmpeg_ok;
  };

  return (
    <>
      {!required && (
        <div className="mb-4">
          <p className="text-sm text-text-muted mb-3">
            You can also transcribe on this computer: free, private, no API key.
            Useful as a backup when you're offline or out of credits.
          </p>
          <div className="flex items-center gap-2 rounded-lg border border-border-subtle bg-surface px-3 py-2">
            <input
              type="checkbox"
              id="enable-local"
              checked={enabled}
              onChange={(e) => onSetEnabled(e.target.checked)}
              className="cursor-pointer"
            />
            <label
              htmlFor="enable-local"
              className="text-sm text-text cursor-pointer"
            >
              Also enable offline / local transcription
            </label>
          </div>
        </div>
      )}

      {required && (
        <p className="text-sm text-text-muted mb-4">
          One question first, so anyscribe can suggest a model for your audio and this
          computer. Or pick a card yourself.
        </p>
      )}

      {(enabled || required) && ffmpegMissing && <FfmpegNotice onCheckAgain={checkFfmpeg} />}

      {(enabled || required) &&
        (status ? (
          <LocalModelPicker
            models={models}
            featured={status.featured}
            languageAnswers={status.language_answers}
            caption={status.benchmark_caption}
            selected={selected}
            onSelect={onSelectSize}
            disabled={settingUp}
            guideOpen={required}
            onRecommendation={(r) => {
              setRec(r);
              onSelectSize(r.primary); // "nothing fits" clears it: no download offered
            }}
            onSetLanguage={onSetLanguage}
          />
        ) : (
          <div className="text-xs text-text-muted font-mono py-4">Loading models…</div>
        ))}

      {status?.restart_needed && <RestartBanner />}

      {setupError && (
        <div className="rounded-md border border-red/30 bg-red/5 px-3 py-2 mb-3 mt-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red mt-0.5 shrink-0" />
            <p className="text-xs text-red font-mono break-words">
              {setupError.length > 500 ? setupError.slice(0, 500) + "…" : setupError}
            </p>
          </div>
        </div>
      )}

      {missing && (
        <div role="alert" className="rounded-md border border-red/30 bg-red/5 px-3 py-2 mb-3 mt-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red mt-0.5 shrink-0" />
            <p className="text-xs text-red">{missing}</p>
          </div>
        </div>
      )}

      {(settingUp || logLines.length > 0) && (enabled || required) && (
        <div className="my-4">
          <div className="rounded-md border border-border-subtle bg-surface-raised px-3 py-2">
            <div className="flex items-center gap-2">
              {settingUp && <Loader2 className="w-4 h-4 animate-spin text-amber" />}
              <p className="text-xs text-text font-mono">
                {settingUp
                  ? status?.setup_progress?.percent != null
                    ? `Downloading ${runningName ?? "the model"}… ${status.setup_progress.percent}%`
                    : "Installing the local engines and downloading the model…"
                  : "Install log"}
              </p>
            </div>
          </div>
          <button
            onClick={() => setLogOpen(!logOpen)}
            className="mt-2 text-[10px] font-mono text-text-muted hover:text-text cursor-pointer"
          >
            {logOpen ? "hide" : "show"} install log ({logLines.length} lines)
          </button>
          {logOpen && (
            <pre className="mt-1 max-h-48 overflow-auto rounded-md border border-border-subtle bg-black/20 p-2 text-[10px] font-mono text-text-muted whitespace-pre-wrap break-all">
              {logLines.length > 0 ? logLines.join("\n") : "(no output yet)"}
            </pre>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mt-5">
        <button
          onClick={onBack}
          disabled={settingUp}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
        >
          <ChevronLeft className="w-3 h-3" />
          Back
        </button>
        <div className="flex items-center gap-2">
          {(enabled || required) && (
            <button
              onClick={handleStartSetup}
              disabled={!selected || settingUp || ffmpegMissing}
              className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
            >
              {settingUp ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Setting up…
                </>
              ) : !pick ? (
                "Install now"
              ) : downloadMb > 0 ? (
                `Download ${names.join(" + ")} (${formatMB(downloadMb)})`
              ) : allRunnable && status?.runtime_ready ? (
                <>
                  Installed — continue
                  <ChevronRight className="w-3 h-3" />
                </>
              ) : (
                `Set up ${names.join(" + ")}`
              )}
            </button>
          )}
          {!required && !enabled && (
            <button
              onClick={onNext}
              className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer flex items-center gap-1"
            >
              Skip, next
              <ChevronRight className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
      {(enabled || required) && ffmpegMissing && (
        <p className="mt-2 text-right text-[11px] text-text-muted">
          Install ffmpeg first (see above), then click Check again.
        </p>
      )}
    </>
  );
}

/** Setup ended without an error but local still can't run: say which part. */
function missingPart(s: LocalStatusResponse): string {
  if (!s.faster_whisper_installed) {
    return s.restart_needed
      ? "Setup finished, but the local engine can't load until anyscribe restarts. Quit anyscribe and open it again, then continue."
      : "Setup finished, but the local engine (faster-whisper) isn't installed. Open the install log below for details, then try again.";
  }
  return "Setup finished, but no model can run yet. Click the button below to try the download again.";
}

function StepWorkspace({
  defaultPath,
  value,
  onChange,
  onBack,
  onNext,
}: {
  defaultPath: string;
  value: string;
  onChange: (v: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <>
      <p className="text-sm text-text-muted mb-4">
        anyscribe writes transcripts into an Obsidian-compatible vault. Default
        is fine for most users.
      </p>
      <div className="mb-4">
        <label className="block text-xs font-mono text-text-muted mb-1">
          Workspace path
        </label>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={defaultPath || "~/anyscribe"}
          className="w-full bg-surface-raised border border-border rounded-md px-3 py-2 text-sm text-text font-mono outline-none focus:border-amber/40"
        />
        <p className="text-[10px] font-mono text-text-muted mt-1">
          Leave blank to use the default ({defaultPath || "~/anyscribe"}).
        </p>
      </div>
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer flex items-center gap-1"
        >
          <ChevronLeft className="w-3 h-3" />
          Back
        </button>
        <button
          onClick={onNext}
          className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer flex items-center gap-1"
        >
          Next
          <ChevronRight className="w-3 h-3" />
        </button>
      </div>
    </>
  );
}

function StepDone({
  form,
  name,
  saving,
  onBack,
  onFinish,
}: {
  form: FormState;
  name: (id: string) => string;
  saving: boolean;
  onBack: () => void;
  onFinish: () => void;
}) {
  const cloud = API_PROVIDERS.find((p) => p.name === form.provider);
  return (
    <>
      {form.restartNeeded && <RestartBanner />}
      <p className="text-sm text-text-muted mb-4">
        One click and we'll save everything. You can change any of this in
        Settings later.
      </p>
      <div className="rounded-lg border border-border-subtle bg-surface-raised p-4 mb-5 space-y-2">
        <SummaryRow
          label="Transcribe"
          value={form.provider === "local" ? "On this computer" : cloud?.label ?? form.provider ?? "—"}
        />
        {form.provider && form.provider !== "local" && form.apiKey && (
          <SummaryRow label="API key" value="••••" />
        )}
        {form.localModel && (form.provider === "local" || form.enableLocal) && (
          <SummaryRow
            label={form.provider === "local" ? "Model" : "Offline model"}
            value={`${name(form.localModel)} · ready`}
          />
        )}
        {form.language && <SummaryRow label="Language" value="Hindi" />}
        <SummaryRow
          label="Workspace"
          value={form.workspace || "(default)"}
        />
        {form.alsoModels.length > 0 && (
          <div className="pt-1 border-t border-border-subtle">
            <ExtraDownloads
              ids={form.alsoModels}
              name={name}
              pendingNote={`Switching to ${form.alsoModels.map(name).join(" + ")} for Hindi and other languages works once it finishes downloading. You can start transcribing now; the download carries on.`}
            />
          </div>
        )}
      </div>
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          disabled={saving}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
        >
          <ChevronLeft className="w-3 h-3" />
          Back
        </button>
        <button
          onClick={onFinish}
          disabled={saving}
          className="rounded-md bg-amber text-surface px-4 py-2 text-sm font-mono hover:bg-amber/80 transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-2"
        >
          {saving ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Saving…
            </>
          ) : (
            <>
              <Check className="w-3.5 h-3.5" />
              Finish &amp; start transcribing
            </>
          )}
        </button>
      </div>
    </>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs font-mono text-text-muted">{label}</span>
      <span className="text-xs font-mono text-text">{value}</span>
    </div>
  );
}
