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
import { TerminalFlow } from "./MacCards";
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
  | "done"
  | "terminal"; // Mac app only: the optional last step, after Finish saved

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

// Every status read (and the start request) gives up after this, so a quit or
// stuck server shows as unreachable instead of a silent wait.
const REQUEST_LIMIT_MS = 10_000;
const POLL_MS = 1500;

// Try again does not resume a half-downloaded model: a real download stopped at
// 35.6% restarted from 0% (docs/reviews/2026-11-20-onboarding-wave1-lock/proof.md, rule 12).
const S12 =
  "Can't reach anyscribe right now. If you closed it, the download stopped too: open anyscribe again and this page shows a Try again button to start it again.";
// no cause named: the server answers the same after a restart and when the start never reached it
const S14 = "Setup didn't finish. Click Try again to start it again.";
// the server's own error text (installer stderr, HTTP details) stays in the install log
const SETUP_FAILED = "anyscribe couldn't finish setting up local transcription.";

/** Send a request with a time limit; ``ctl`` lets the caller abort it too. */
function limited<T>(
  send: (signal: AbortSignal) => Promise<T>,
  ctl = new AbortController()
): Promise<T> {
  const timer = setTimeout(() => ctl.abort(), REQUEST_LIMIT_MS);
  return send(ctl.signal).finally(() => clearTimeout(timer));
}

interface Props {
  onClose: () => void;
  /** Mac app, Terminal not yet asked: after Finish, offer it as the last step; called once answered. */
  offerTerminal?: () => void;
}

export default function OnboardingWizard({ onClose, offerTerminal }: Props) {
  const [step, setStepNow] = useState<Step>("welcome");
  // Read by the opening status reply when it lands (review L1). Shown: the
  // local step was ever asked for, set with the step itself. Heard: on any
  // visit, the step accepted a status read of its own, which is newer than the
  // reply (a start needs one first: the pick comes from it).
  const localShownRef = useRef(false);
  const heardRef = useRef(false);
  const setStep = useCallback((s: Step) => {
    if (s === "offline_opt_in") localShownRef.current = true;
    setStepNow(s);
  }, []);
  const onHeard = useCallback(() => {
    heardRef.current = true;
  }, []);
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
  // reported by the local step alone: a setup is watched, so closing asks first (S11)
  const [watched, setWatched] = useState(false);
  const [confirmClose, setConfirmClose] = useState(false);
  const onWatched = useCallback((w: boolean) => {
    setWatched(w);
    if (!w) setConfirmClose(false); // nothing left to warn about
  }, []);
  // The opening read's running reply, handed to the local step, which decides
  // whether to watch it. Cleared when that step is left, so it is used once.
  const [adopt, setAdopt] = useState<LocalStatusResponse | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [defaultWorkspace, setDefaultWorkspace] = useState("");
  const modelName = useLocalModelNames(); // fetched now, so All set shows names at once
  // The recommended card as the starting pick, unless a pick was made first
  // (a functional update, so a late status response can't undo a choice).
  const presetSize = useCallback(
    (s: string) => setForm((f) => (f.localModel ? f : { ...f, localModel: s })),
    []
  );
  // stable, so the local step's effects don't rerun on every wizard render
  const setEnableLocal = useCallback(
    (e: boolean) => setForm((f) => ({ ...f, enableLocal: e })),
    []
  );
  const selectSize = useCallback(
    (s: string | null) => setForm((f) => ({ ...f, localModel: s })),
    []
  );
  const setupDone = useCallback(
    (done: Pick<FormState, "alsoModels" | "restartNeeded">) => setForm((f) => ({ ...f, ...done })),
    []
  );
  const goWorkspace = useCallback(() => {
    setAdopt(null);
    setStep("workspace");
  }, [setStep]);

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
  // started one): open on it instead of offering Download again. Routes and
  // hands the step what it read; the step reports whether a setup is watched.
  // What the wizard has heard when the reply lands decides what it may do (L1).
  useEffect(() => {
    const ctl = new AbortController(); // aborted once this wizard closes (or StrictMode replays the effect)
    limited(getLocalStatus, ctl)
      .then((s) => {
        // heard: the step's own accepted read is newer
        if (!s.setup_running || heardRef.current) return;
        // shown before: the step takes it, now if mounted, else at its next
        // mount; the form and the route stay
        if (localShownRef.current) return setAdopt(s);
        setForm((f) => ({
          ...f,
          provider: "local",
          enableLocal: true,
          localModel: s.setup_last_model,
        }));
        setAdopt(s);
        setStep("offline_opt_in");
      })
      .catch(() => undefined);
    return () => ctl.abort();
  }, [setStep]);

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
  // While a setup is watched, closing asks first (S11)
  const askOrClose = (persist: boolean) => (watched ? setConfirmClose(true) : dismiss(persist));

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
      if (offerTerminal) setStep("terminal");
      else dismiss(true);
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
      // with the confirmation open, Escape (and a click outside) means Keep setting up
      onClose={() => {
        if (confirmClose) return setConfirmClose(false);
        // the Terminal step is asked once: Escape or a click outside answers Skip for now (C6)
        if (step === "terminal" && offerTerminal) {
          offerTerminal();
          return askOrClose(true);
        }
        askOrClose(false);
      }}
      disableClose={saving}
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
          {step !== "welcome" && step !== "done" && step !== "terminal" && (
            <p className="text-[10px] font-mono text-text-muted mt-0.5">
              Step {stepIndex}
              {form.provider ? ` of ${path.length}` : ""}
            </p>
          )}
        </div>
        {step !== "done" && step !== "terminal" && !saving && (
          <button
            onClick={() => askOrClose(true)}
            className="flex items-center gap-1 text-xs font-mono text-text-muted hover:text-text transition-colors cursor-pointer"
            aria-label="Skip onboarding"
          >
            Skip for now
            <X className="w-3 h-3" />
          </button>
        )}
      </div>
      {watched && (
        <p className="-mt-2 mb-4 text-xs font-mono text-text-muted">
          Back is off until setup finishes. Skip for now asks first.
        </p>
      )}

      {confirmClose && (
        <div role="alertdialog" aria-label="Close setup?" className="rounded-md border border-amber/40 bg-amber/[0.08] px-3 py-2.5 mb-4">
          <p className="text-xs text-text">
            Close setup? The download keeps going in the background while anyscribe stays open.
            Your choices on these screens are saved only when you click Finish. To come back:
            Settings, then Run setup wizard.
          </p>
          <div className="mt-2 flex justify-end gap-2">
            <button
              // focus scrolls it into view in the dialog and takes keyboard users to the choice
              autoFocus
              onClick={() => setConfirmClose(false)}
              className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text hover:bg-surface-raised transition-colors cursor-pointer"
            >
              Keep setting up
            </button>
            <button
              onClick={() => dismiss(false)}
              className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer"
            >
              Close setup
            </button>
          </div>
        </div>
      )}

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
          onSetEnabled={setEnableLocal}
          onSelectSize={selectSize}
          onPresetSize={presetSize}
          onSetLanguage={(code) => setForm((f) => ({ ...f, language: code }))}
          onSetupDone={setupDone}
          adopt={adopt}
          onRunning={onWatched}
          onHeard={onHeard}
          onBack={() => {
            setAdopt(null);
            setStep(form.provider === "local" ? "provider" : "api_key");
          }}
          onNext={goWorkspace}
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
      {step === "terminal" && offerTerminal && (
        <TerminalFlow
          eyebrow="Last step · optional"
          onDone={() => {
            offerTerminal();
            dismiss(true);
          }}
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
    case "terminal":
      return "One last thing";
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
  // Sarvam has no way to check a key in advance: say so up front, and Next just goes on.
  const uncheckable = providerName === "sargam";

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
    if (uncheckable) return onNext();
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
      {uncheckable && (
        <p className="text-xs text-amber border-l-[3px] border-amber bg-amber/[0.07] rounded-md px-3 py-2 mb-4">
          Not checked yet: Sarvam has no way to check a key in advance. It will be checked on your
          first transcript.
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
          {!uncheckable && (
            <button
              onClick={runCheck}
              disabled={!value || testing}
              className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50"
            >
              Test key
            </button>
          )}
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
  adopt,
  onRunning,
  onHeard,
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
  /** the wizard's opening read saw a setup running: watch it, unless something newer spoke */
  adopt: LocalStatusResponse | null;
  onRunning: (watched: boolean) => void;
  /** the step accepted a status read of its own (review L1) */
  onHeard: () => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const [status, setStatus] = useState<LocalStatusResponse | null>(null);
  // watching: a setup is (or may be) running, so the step reads its status
  // a reply handed before mount is accepted on the first render
  const [watching, setWatching] = useState(adopt !== null);
  const [starting, setStarting] = useState(false); // the start request hasn't settled
  // +1 when a start request is sent and again when it settles (odd: in flight).
  // A status read speaks for the setup only if this was even and unchanged
  // from sending to answer: one sent before the start settled can neither
  // start nor end watching.
  const startGenRef = useRef(0);
  const busy = watching || starting;
  // two status reads in a row failed or timed out
  const [unreachable, setUnreachable] = useState(false);
  const failsRef = useRef(0);
  // setup ended or was refused and the pick can't run: one plain sentence, and
  // the button says Try again (ffmpeg shows its own notice)
  const [missing, setMissing] = useState<string | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [logOpen, setLogOpen] = useState(false);
  const logCursorRef = useRef(0);
  const [rec, setRec] = useState<LocalRecommendation | null>(null);
  const haveStatus = status !== null;

  // The wizard's "closing asks first" has this one writer (busy: from the
  // click, not only once watching), and goes back to false with the step.
  useEffect(() => {
    const report = (w: boolean) => onRunning(w);
    report(busy);
    return () => report(false);
  }, [busy, onRunning]);

  // A handed reply counts only if this step has no accepted read of its own.
  // The wizard drops a reply once the step accepted a read on any visit; this
  // covers a read accepted in the same render as the hand-off.
  // Taken while rendering, so the render that receives it already watches.
  const [taken, setTaken] = useState<LocalStatusResponse | null>(null);
  if (adopt && adopt !== taken && status === null) {
    setTaken(adopt);
    setWatching(true);
  }
  // and the wizard's form follows it: local on, the running model picked
  useEffect(() => {
    if (!taken) return;
    onSetEnabled(true);
    if (taken.setup_last_model) onSelectSize(taken.setup_last_model);
  }, [taken, onSetEnabled, onSelectSize]);

  // One status read at a time, each with a time limit: until the first status
  // arrives, then for as long as a setup is watched. Watching ends only on a
  // good read, sent after the start request settled, that says it stopped.
  useEffect(() => {
    if (haveStatus && !watching) return;
    let stop = false;
    let ctl: AbortController | undefined;
    let next: ReturnType<typeof setTimeout> | undefined;
    const tick = async () => {
      const gen = startGenRef.current;
      ctl = new AbortController();
      const s = await limited(getLocalStatus, ctl).catch(() => null);
      // the log is read on its own: a failed log read changes only the log panel
      ctl = new AbortController();
      const log =
        s && watching
          ? await limited((sig) => getSetupLog(logCursorRef.current, sig), ctl).catch(() => null)
          : null;
      if (stop) return; // this loop was replaced or the step closed: drop the answer
      if (log && log.lines.length > 0) {
        setLogLines((prev) => [...prev, ...log.lines]);
        logCursorRef.current = log.total;
      }
      if (!s) {
        failsRef.current += 1;
        if (failsRef.current >= 2) setUnreachable(true);
      } else if (gen === startGenRef.current && gen % 2 === 0) {
        // (otherwise it was sent before the start request settled: ignored)
        failsRef.current = 0;
        setUnreachable(false);
        setStatus(s);
        onHeard();
        onPresetSize(s.recommended_model);
        if (s.setup_running) {
          // watch the running setup, with its progress and its model
          if (!watching) onSetEnabled(true);
          if (s.setup_last_model && s.setup_last_model !== selected) onSelectSize(s.setup_last_model);
          setWatching(true);
        } else if (watching) {
          // the one read that ends watching: its branch runs once
          stop = true;
          setWatching(false);
          if (s.setup_error) {
            setMissing(`${SETUP_FAILED} Click Try again; if it fails again, ${otherwise(required)}.`);
          } else if (s.set_up && s.models.find((m) => m.size === selected)?.runnable) {
            // set_up means some model can run: All set names this one as ready.
            // The server queued the extras (Turbo for a mix) itself; All set
            // shows their progress.
            onSetupDone({ alsoModels: s.setup_also, restartNeeded: s.restart_needed });
            onNext();
          } else if (s.ffmpeg_ok) {
            const name = s.models.find((m) => m.size === selected)?.spec.display_name;
            // no outcome and no error: no setup or result is reported (S14)
            setMissing(s.setup_outcome == null ? S14 : missingPart(s, name, required));
          }
          return;
        }
      }
      next = setTimeout(tick, POLL_MS);
    };
    void tick();
    return () => {
      stop = true;
      ctl?.abort();
      clearTimeout(next);
    };
  }, [haveStatus, watching, selected, required, onHeard, onPresetSize, onSetEnabled, onSelectSize, onSetupDone, onNext]);

  // The only way forward with local on: setup (quick when the model can
  // already run) switches the default and queues the extras server-side.
  const handleStartSetup = async () => {
    if (!selected) return;
    startGenRef.current += 1;
    setStarting(true);
    setMissing(null);
    setLogLines([]);
    logCursorRef.current = 0;
    let refused = false;
    try {
      await limited((sig) => setupLocal(selected, keptRec?.also ?? [], sig));
    } catch (e) {
      // Only an answer other than 409 means it didn't start. A 409 (one is
      // already running) or no answer at all (it may have started): watch.
      const msg = e instanceof Error ? e.message : "";
      refused = /^\d{3}:/.test(msg) && !msg.startsWith("409");
    }
    startGenRef.current += 1;
    setStarting(false);
    if (refused) setMissing(`anyscribe couldn't start the setup. Click Try again; if it fails again, ${otherwise(required)}.`);
    else setWatching(true);
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
    const s = await limited(getLocalStatus);
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
              disabled={busy}
              className="cursor-pointer disabled:cursor-not-allowed"
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

      {unreachable && (
        <div role="status" className="rounded-md border border-amber/40 bg-amber/[0.08] px-3 py-2.5 mb-4 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-amber mt-0.5 shrink-0" />
          <p className="text-xs text-text">{S12}</p>
        </div>
      )}

      {(enabled || required) && ffmpegMissing && <FfmpegNotice onCheckAgain={checkFfmpeg} />}

      {status?.restart_needed && (
        <RestartBanner>
          Then open the setup wizard again (Settings, then Run setup wizard); the download is kept.
        </RestartBanner>
      )}

      {(busy || logLines.length > 0) && (enabled || required) && (
        <div className="my-4">
          <div className="rounded-md border border-border-subtle bg-surface-raised px-3 py-2">
            <div className="flex items-center gap-2">
              {busy && <Loader2 className="w-4 h-4 animate-spin text-amber" />}
              <p className="text-xs text-text font-mono">
                {busy
                  ? unreachable
                    ? "Waiting for anyscribe…"
                    : status?.setup_progress?.percent != null
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

      {(enabled || required) &&
        (status ? (
          <LocalModelPicker
            models={models}
            featured={status.featured}
            languageAnswers={status.language_answers}
            caption={status.benchmark_caption}
            selected={selected}
            onSelect={onSelectSize}
            disabled={busy}
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

      {/* just above the buttons, so the Try again it names is in view */}
      {missing && (
        <div role="alert" className="rounded-md border border-red/30 bg-red/5 px-3 py-2 mt-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red mt-0.5 shrink-0" />
            <p className="text-xs text-red">{missing}</p>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mt-5">
        <button
          onClick={onBack}
          disabled={busy}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
        >
          <ChevronLeft className="w-3 h-3" />
          Back
        </button>
        <div className="flex items-center gap-2">
          {(enabled || required) && (
            <button
              onClick={handleStartSetup}
              disabled={!selected || busy || ffmpegMissing}
              className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
            >
              {busy ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Setting up…
                </>
              ) : missing ? (
                "Try again"
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
          Install ffmpeg first (see above).
        </p>
      )}
    </>
  );
}

/** The way on when local setup keeps failing. */
function otherwise(required: boolean): string {
  return required ? "choose a cloud service instead" : "untick local transcription and go on";
}

/** Setup ended without an error but the picked model can't run: say why,
 * plainly. Null when a restart is due: the RestartBanner says it alone. */
function missingPart(s: LocalStatusResponse, name: string | undefined, required: boolean): string | null {
  if (!s.faster_whisper_installed && s.restart_needed) return null;
  if (!s.faster_whisper_installed) {
    return `A part anyscribe needs to transcribe on this computer didn't install. Click Try again; if it fails again, ${otherwise(required)}.`;
  }
  return `Setup finished, but ${name ?? "the model"} can't run yet. Click Try again; if it fails again, ${otherwise(required)}.`;
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
