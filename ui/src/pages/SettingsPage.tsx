import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  getConfig,
  updateConfig,
  getProviders,
  testProvider,
  getHealth,
  updateKey,
  deleteKey,
  getLocalStatus,
  chooseLocal,
  pullLocalModel,
  deleteLocalModel,
  reinstallLocalModel,
  teardownLocal,
  getAutostart,
  setAutostart,
  TailnetError,
} from "../api/client";
import type { AutostartState } from "../api/client";
import type {
  Config,
  Provider,
  ProviderTestResult,
  LocalStatusResponse,
  ResolvedRun,
} from "../api/types";
import LanguageInput from "../components/LanguageInput";
import ModelInput from "../components/ModelInput";
import { defaultModelFor, extraModelsFor, tierSummary } from "../api/models";
import LocalSetupModal from "../components/LocalSetupModal";
import LocalModelPicker from "../components/LocalModelPicker";
import { RestartBanner } from "../components/LocalSetupNotes";
import Toggle from "../components/Toggle";
import ThisMac from "../components/ThisMac";
import { desktop } from "../desktop";
import { TailnetLink } from "../components/TailnetShare";
import { REMOTE, useTailnet } from "../hooks/useTailnet";
import {
  Check,
  AlertCircle,
  Loader2,
  ChevronUp,
  ChevronDown,
  Key,
  Sparkles,
  Download,
  Trash2,
  RefreshCw,
  PlayCircle,
  X,
} from "lucide-react";

const MB = 1024 * 1024;

export default function SettingsPage() {
  const location = useLocation();
  const [config, setConfig] = useState<Config | null>(null);
  const localModel = config?.local_model;
  const [providers, setProviders] = useState<Provider[]>([]);
  const [health, setHealth] = useState<{
    ok: boolean;
    version: string;
    dependencies: Record<string, boolean>;
  } | null>(null);
  const [localStatus, setLocalStatus] = useState<LocalStatusResponse | null>(
    null
  );
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<
    Record<string, ProviderTestResult>
  >({});
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState("");
  const [savingKey, setSavingKey] = useState(false);
  const [keySaved, setKeySaved] = useState<string | null>(null);
  const [confirmOverwrite, setConfirmOverwrite] = useState(false);
  const [confirmRemoveKey, setConfirmRemoveKey] = useState(false);
  const [removingKey, setRemovingKey] = useState(false);
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [pullingSize, setPullingSize] = useState<string | null>(null);
  const [deletingSize, setDeletingSize] = useState<string | null>(null);
  const [reinstallingSize, setReinstallingSize] = useState<string | null>(null);
  const [confirmTeardown, setConfirmTeardown] = useState(false);
  const [tearingDown, setTearingDown] = useState(false);
  // null = unsupported platform or unreachable; the row renders nothing.
  const [autostart, setAutostartState] = useState<AutostartState | null>(null);

  useEffect(() => {
    getAutostart()
      .then(setAutostartState)
      .catch(() => setAutostartState(null));
  }, []);

  const handleAutostart = async (v: boolean) => {
    setError(null);
    try {
      setAutostartState(await setAutostart(v));
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to change open-at-login"
      );
    }
  };

  const refreshAll = useCallback(async () => {
    const [c, p, h, l] = await Promise.all([
      getConfig(),
      getProviders(),
      getHealth(),
      getLocalStatus(),
    ]);
    setConfig(c);
    setProviders(p);
    setHealth(h);
    setLocalStatus(l);
  }, []);

  useEffect(() => {
    const id = window.setTimeout(() => {
      void refreshAll();
    }, 0);
    return () => window.clearTimeout(id);
  }, [refreshAll]);

  // Deep-link from Transcribe page CTA.
  useEffect(() => {
    if (location.hash !== "#api-keys" || !config) return;
    const el = document.getElementById("api-keys");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [location.hash, config]);

  // Poll local status while any long-running local operation is in flight.
  // Now includes queued downloads (not just the running one).
  useEffect(() => {
    const anyQueueActivity = (localStatus?.models || []).some(
      (m) => m.downloading || m.queued
    );
    if (
      !pullingSize &&
      !deletingSize &&
      !reinstallingSize &&
      !localStatus?.setup_running &&
      !anyQueueActivity &&
      localStatus?.pending_default?.state !== "downloading"
    )
      return;
    const id = setInterval(async () => {
      try {
        const [l, p] = await Promise.all([getLocalStatus(), getProviders()]);
        setLocalStatus(l);
        setProviders(p);
        if (pullingSize) {
          const entry = l.models.find((m) => m.size === pullingSize);
          if (entry?.runnable) setPullingSize(null);
        }
        // the server switched the default once a chosen model could run
        if (l.default_model !== localModel) setConfig(await getConfig());
      } catch {
        // transient
      }
    }, 1500);
    return () => clearInterval(id);
  }, [
    pullingSize,
    deletingSize,
    reinstallingSize,
    localStatus?.setup_running,
    localStatus?.models,
    localStatus?.pending_default?.state,
    localModel,
  ]);

  // Any explicit model choice (a card click, or "Use …" under Help me
  // choose). The server makes it the default once it can run, now if it
  // already can, downloading what it needs; a later choice replaces it.
  const chooseLocalModel = async (size: string, also: string[] = []) => {
    setError(null);
    try {
      await chooseLocal(size, also);
      const [c, l] = await Promise.all([getConfig(), getLocalStatus()]);
      setConfig(c);
      setLocalStatus(l);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to choose ${size}`);
    }
  };

  const handleSave = async (updates: Partial<Config>) => {
    if (!config) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateConfig(updates);
      setConfig(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save setting");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (name: string) => {
    setTestingProvider(name);
    setError(null);
    try {
      const result = await testProvider(name);
      setTestResults((prev) => ({ ...prev, [name]: result }));
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to test ${name}`);
    } finally {
      setTestingProvider(null);
    }
  };

  const handlePull = async (size: string) => {
    setPullingSize(size);
    setError(null);
    try {
      await pullLocalModel(size);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to download ${size}`);
      setPullingSize(null);
    }
  };

  const handleDelete = async (size: string) => {
    setDeletingSize(size);
    setError(null);
    try {
      await deleteLocalModel(size);
      const l = await getLocalStatus();
      setLocalStatus(l);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to delete ${size}`);
    } finally {
      setDeletingSize(null);
    }
  };

  const handleReinstall = async (size: string) => {
    setReinstallingSize(size);
    setError(null);
    try {
      await reinstallLocalModel(size);
      const l = await getLocalStatus();
      setLocalStatus(l);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to reinstall ${size}`);
    } finally {
      setReinstallingSize(null);
    }
  };

  const handleTeardown = async () => {
    setTearingDown(true);
    setError(null);
    try {
      await teardownLocal();
      await refreshAll();
      setConfirmTeardown(false);
      setExpandedProvider(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove local");
    } finally {
      setTearingDown(false);
    }
  };

  if (!config) {
    return (
      <div className="px-4 sm:px-8 py-10 max-w-3xl">
        <div className="h-8 w-32 bg-surface rounded animate-pulse mb-6" />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-surface rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const localName = (id: string) =>
    localStatus?.models.find((m) => m.size === id)?.spec.display_name ?? id;
  const selectedProvider = providers.find((p) => p.name === config.provider);
  const providerMissingKey = selectedProvider && !selectedProvider.has_key;
  const currentDefaultModel =
    config.provider === "local"
      ? localName(config.local_model)
      : defaultModelFor(selectedProvider, config.provider_models);

  // Language codes differ per provider, so the picker follows whichever
  // provider the current quality knob actually resolves to.
  const activeTier = tierSummary(config.quality, config, providers);
  const effectiveProvider =
    activeTier.provider && activeTier.hasKey ? activeTier.provider : config.provider;
  // A local user doesn't need a key: cloud rows say so quietly, not as a warning.
  const localUser = (config.quality === "custom" ? config.provider : activeTier.provider) === "local";
  const keyWarn = (provider: string) =>
    provider === "local" ? "not set up" : localUser ? "add a key to use" : "needs API key";

  const handlePin = (provider: string, model: string) =>
    handleSave({
      provider_models: { ...(config.provider_models ?? {}), [provider]: model },
    });

  const handleExtras = async (provider: string, models: string[]) => {
    await handleSave({
      extra_models: { ...(config.extra_models ?? {}), [provider]: models },
    });
    // The merged model lists on /api/providers changed — refresh the pickers.
    setProviders(await getProviders());
  };

  return (
    <div className="px-4 sm:px-8 py-10 max-w-3xl">
      {localStatus?.restart_needed && <RestartBanner />}
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1
          className="text-2xl font-bold tracking-tight text-text"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Settings
        </h1>
        <div className="flex items-center gap-3">
          {saved && (
            <span className="flex items-center gap-1 text-xs text-green animate-fade-in">
              <Check className="w-3 h-3" />
              Saved
            </span>
          )}
          <button
            onClick={() => {
              const w = window as unknown as { openOnboarding?: () => void };
              w.openOnboarding?.();
            }}
            className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer"
            title="Re-run the onboarding wizard"
          >
            <PlayCircle className="w-3 h-3" />
            Run setup wizard
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded-lg border border-red/30 bg-red/5 px-4 py-2 mb-6 flex items-center justify-between animate-slide-up">
          <p className="text-xs text-red font-mono">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-red/60 hover:text-red text-xs ml-4 cursor-pointer"
          >
            dismiss
          </button>
        </div>
      )}

      {/* Mac app: This Mac replaces Startup. Browser: Startup, hidden only where the API says unsupported. */}
      {desktop ? (
        <ThisMac workspace={config._resolved_workspace} />
      ) : autostart?.supported && (
        <section className="mb-10">
          <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
            Startup
          </h2>
          <div className="rounded-lg border border-border-subtle bg-surface px-4 py-3">
            <SettingRow label="Start at login">
              <Toggle
                value={autostart.enabled}
                onChange={(v) => void handleAutostart(v)}
              />
            </SettingRow>
            <p className="text-xs text-text-muted mt-1">
              Starts anyscribe in the background when you log in.
            </p>
          </div>
        </section>
      )}

      {/* Configure Defaults */}
      <section className="mb-10">
        <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
          Configure Defaults
        </h2>
        <div className="space-y-4">
          {/* Lead with the answer: what the next run actually uses. Re-rendered
              from every PUT response, so it live-updates as knobs change. */}
          <NextRun resolved={config._resolved} />

          {/* One knob picks the provider: a tier, or "custom" to pick by hand.
              Captions show what each tier resolves to right now. */}
          <div>
            <label className="text-sm text-text-secondary">What runs by default</label>
            <div className="mt-2 rounded-lg border border-border-subtle overflow-hidden">
              {["accuracy", "balanced", "cost", "free"].map((tier) => {
                const s = tierSummary(tier, config, providers);
                return (
                  <QualityChoice
                    key={tier}
                    name={tier}
                    caption={
                      s.provider +
                      (s.model ? ` · ${s.provider === "local" ? localName(s.model) : s.model}` : "")
                    }
                    warn={s.hasKey ? null : keyWarn(s.provider)}
                    muted={localUser && s.provider !== "local"}
                    selected={config.quality === tier}
                    disabled={saving}
                    onSelect={() => handleSave({ quality: tier })}
                  />
                );
              })}
              <QualityChoice
                name="custom"
                caption={
                  config.provider +
                  (currentDefaultModel ? ` · ${currentDefaultModel}` : "")
                }
                warn={providerMissingKey ? keyWarn(config.provider) : null}
                selected={config.quality === "custom"}
                disabled={saving}
                onSelect={() => handleSave({ quality: "custom" })}
              />
            </div>
          </div>

          {/* Always visible — a selected tier must never hide the manual
              provider/model controls, it just explains that it outranks them. */}
          <div className="rounded-lg border border-border-subtle bg-surface px-4 py-3 space-y-3">
            <SettingRow label="Provider">
              <select
                value={config.provider}
                onChange={(e) => handleSave({ provider: e.target.value })}
                disabled={saving}
                className="bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40 w-48"
              >
                {providers.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name}
                    {p.has_key ? "" : " · needs key"}
                  </option>
                ))}
              </select>
            </SettingRow>

            {config.quality !== "custom" && (
              <p className="text-xs text-text-muted -mt-1">
                Active tier decides the provider — picking one here switches to
                custom so your choice sticks.
              </p>
            )}

            <SettingRow label="Model">
              {config.provider === "local" ? (
                <span className="text-xs font-mono text-text-muted">
                  {localName(config.local_model)} · change it on the local card below
                </span>
              ) : (
                <ModelInput
                  provider={selectedProvider}
                  value={currentDefaultModel}
                  onChange={(v) => handlePin(config.provider, v)}
                  disabled={saving}
                  className="bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40 w-48"
                />
              )}
            </SettingRow>

            {selectedProvider?.freeform_model && (
              <ExtraModels
                provider={config.provider}
                models={extraModelsFor(config, config.provider)}
                disabled={saving}
                onChange={(list) => handleExtras(config.provider, list)}
              />
            )}
          </div>

          <SettingRow label="Default language">
            <LanguageInput
              provider={effectiveProvider}
              value={config.language}
              onChange={(v) => setConfig({ ...config, language: v })}
              onBlur={(v) => {
                if (v !== config.language) handleSave({ language: v });
              }}
              className="bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40 w-48"
            />
          </SettingRow>

          <SettingRow label="Output format">
            <div className="flex rounded-md border border-border overflow-hidden">
              {["clean", "timestamped", "diarized"].map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => {
                    const updates: Partial<Config> = { output_format: fmt };
                    if (fmt === "diarized") updates.diarize = true;
                    handleSave(updates);
                  }}
                  className={`px-3 py-1.5 text-xs font-mono transition-colors cursor-pointer ${
                    config.output_format === fmt
                      ? "bg-amber/15 text-amber border-r border-border"
                      : "bg-surface-raised text-text-muted hover:text-text border-r border-border"
                  }`}
                >
                  {fmt === "diarized" ? "with-speaker-labels" : fmt}
                </button>
              ))}
            </div>
          </SettingRow>

          <SettingRow label="Multi-speaker by default">
            <Toggle
              value={config.diarize}
              onChange={(v) => handleSave({ diarize: v })}
            />
          </SettingRow>
        </div>
      </section>

      {/* Downloads & media */}
      <section className="mb-10">
        <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
          Downloads &amp; media
        </h2>
        <div className="rounded-lg border border-border-subtle bg-surface px-4 py-3 space-y-3">
          <SettingRow label="After transcribing a URL">
            <select
              value={config.prompt_download}
              onChange={(e) => handleSave({ prompt_download: e.target.value })}
              disabled={saving}
              className="bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40 w-56"
            >
              <option value="never">Just transcribe</option>
              <option value="always">Also download the video</option>
              <option value="ask">Ask each time</option>
            </select>
          </SettingRow>

          <SettingRow label="When transcribing a local file">
            <select
              value={config.local_file_media}
              onChange={(e) => handleSave({ local_file_media: e.target.value })}
              disabled={saving}
              className="bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40 w-56"
            >
              <option value="skip">Leave the file where it is</option>
              <option value="copy">Copy it into the workspace</option>
              <option value="move">Move it into the workspace</option>
              <option value="ask">Ask each time</option>
            </select>
          </SettingRow>

          <SettingRow label="Keep media">
            <Toggle
              value={config.keep_media}
              onChange={(v) => handleSave({ keep_media: v })}
            />
          </SettingRow>

          <SettingRow label="Instagram cookies from browser">
            <select
              value={config.instagram?.browser ?? ""}
              onChange={(e) => handleSave({ instagram: { browser: e.target.value } })}
              disabled={saving}
              className="w-48 bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40"
            >
              <option value="">none (public posts only)</option>
              {["firefox", "chrome", "safari", "brave", "edge", "chromium", "vivaldi", "opera"].map(
                (b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                )
              )}
            </select>
          </SettingRow>
        </div>
      </section>

      {/* Providers */}
      <section className="mb-10" id="api-keys">
        <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
          Providers
        </h2>
        <div className="space-y-2">
          {providers.map((p) => {
            const testResult = testResults[p.name];
            const isExpanded = expandedProvider === p.name;
            const isLocal = p.name === "local";

            if (isLocal) {
              return (
                <LocalProviderCard
                  key={p.name}
                  provider={p}
                  status={localStatus}
                  isExpanded={isExpanded}
                  testResult={testResult}
                  testing={testingProvider === p.name}
                  pullingSize={pullingSize}
                  deletingSize={deletingSize}
                  reinstallingSize={reinstallingSize}
                  config={config}
                  onToggleExpand={() =>
                    setExpandedProvider(isExpanded ? null : p.name)
                  }
                  onTest={() => handleTest(p.name)}
                  onOpenSetup={() => setShowSetupModal(true)}
                  onPull={handlePull}
                  onDelete={handleDelete}
                  onReinstall={handleReinstall}
                  onDefaultChange={chooseLocalModel}
                  onSetLanguage={async (code) => {
                    await handleSave({ language: code });
                  }}
                  confirmTeardown={confirmTeardown}
                  onTeardownRequest={() => setConfirmTeardown(true)}
                  onTeardownConfirm={handleTeardown}
                  onTeardownCancel={() => setConfirmTeardown(false)}
                  tearingDown={tearingDown}
                />
              );
            }

            return (
              <div
                key={p.name}
                className="rounded-lg border border-border-subtle bg-surface overflow-hidden"
              >
                <div className="flex items-center gap-3 px-4 py-3">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      p.has_key ? "bg-green" : "bg-text-muted/40"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-mono text-text">{p.name}</p>
                    <p className="text-xs text-text-muted truncate">
                      {p.description}
                    </p>
                  </div>
                  <button
                    onClick={() => handleTest(p.name)}
                    disabled={testingProvider === p.name}
                    className="rounded-md border border-border px-2.5 py-1 text-xs text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {testingProvider === p.name ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      "Test"
                    )}
                  </button>
                  {testResult && (
                    <span className={`text-xs ${keyCheckColor(testResult)}`}>
                      {testResult.success && testResult.checked !== false ? (
                        <Check className="w-3.5 h-3.5" />
                      ) : (
                        <AlertCircle className="w-3.5 h-3.5" />
                      )}
                    </span>
                  )}
                  <button
                    onClick={() => {
                      if (isExpanded) {
                        setExpandedProvider(null);
                      } else {
                        setExpandedProvider(p.name);
                        setKeyInput("");
                        setKeySaved(null);
                        setConfirmOverwrite(false);
                        setConfirmRemoveKey(false);
                      }
                    }}
                    className={`rounded-md px-1.5 py-1 transition-colors cursor-pointer ${
                      !p.has_key && !isExpanded
                        ? "text-amber hover:text-amber/80"
                        : "text-text-muted hover:text-text"
                    }`}
                    title={p.has_key ? "Update API key" : "Add API key"}
                  >
                    {isExpanded ? (
                      <ChevronUp className="w-3.5 h-3.5" />
                    ) : !p.has_key ? (
                      <span className="flex items-center gap-1 text-xs font-mono">
                        <Key className="w-3.5 h-3.5" />
                        add key
                      </span>
                    ) : (
                      <Key className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
                {testResult && (
                  <p className={`px-4 pb-3 -mt-1 text-xs ${keyCheckColor(testResult)}`}>
                    {testResult.message}
                  </p>
                )}

                {isExpanded && (
                  <div className="px-4 pb-3 pt-0 border-t border-border-subtle">
                    {(p.models.length > 1 || p.freeform_model) && (
                      <div className="mt-3 space-y-2">
                        <div className="flex items-center gap-2">
                          <label className="text-xs font-mono text-text-muted w-24 shrink-0">
                            Default model
                          </label>
                          <ModelInput
                            provider={p}
                            value={defaultModelFor(p, config.provider_models)}
                            onChange={(v) => handlePin(p.name, v)}
                            disabled={saving}
                          />
                        </div>
                        {p.freeform_model && (
                          <ExtraModels
                            provider={p.name}
                            models={extraModelsFor(config, p.name)}
                            disabled={saving}
                            onChange={(list) => handleExtras(p.name, list)}
                          />
                        )}
                      </div>
                    )}
                    <div className="flex items-center gap-2 mt-3">
                      <input
                        type="password"
                        value={keyInput}
                        onChange={(e) => {
                          setKeyInput(e.target.value);
                          setConfirmOverwrite(false);
                        }}
                        placeholder={
                          p.has_key
                            ? "Enter new key to replace existing"
                            : "Paste API key"
                        }
                        className="flex-1 bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40"
                        autoFocus
                      />
                      <button
                        onClick={async () => {
                          if (!keyInput.trim()) return;
                          if (p.has_key && !confirmOverwrite) {
                            setConfirmOverwrite(true);
                            return;
                          }
                          setSavingKey(true);
                          setConfirmOverwrite(false);
                          setError(null);
                          try {
                            await updateKey(p.name, keyInput.trim());
                            setKeySaved(p.name);
                            setKeyInput("");
                            const updated = await getProviders();
                            setProviders(updated);
                            setTimeout(() => setKeySaved(null), 2000);
                          } catch (err) {
                            setError(
                              err instanceof Error
                                ? err.message
                                : "Failed to save key"
                            );
                          } finally {
                            setSavingKey(false);
                          }
                        }}
                        disabled={savingKey || !keyInput.trim()}
                        className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50"
                      >
                        {savingKey ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : keySaved === p.name ? (
                          <Check className="w-3 h-3 text-green" />
                        ) : confirmOverwrite ? (
                          "Replace?"
                        ) : (
                          "Save"
                        )}
                      </button>
                    </div>
                    {p.key_url && (
                      <p className="text-xs text-text-muted mt-2">
                        Get your key at{" "}
                        <a
                          href={p.key_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-amber hover:underline"
                        >
                          {p.key_url.replace(/^https?:\/\//, "")}
                        </a>
                      </p>
                    )}
                    {p.key_in_env_file && (
                      <div className="mt-3 flex items-center justify-end gap-2">
                        {confirmRemoveKey && (
                          <button
                            onClick={() => setConfirmRemoveKey(false)}
                            className="text-xs font-mono text-text-muted hover:text-text transition-colors cursor-pointer"
                          >
                            Cancel
                          </button>
                        )}
                        <button
                          onClick={async () => {
                            if (!confirmRemoveKey) {
                              setConfirmRemoveKey(true);
                              return;
                            }
                            setRemovingKey(true);
                            setError(null);
                            try {
                              await deleteKey(p.name);
                              setConfirmRemoveKey(false);
                              setExpandedProvider(null);
                              const updated = await getProviders();
                              setProviders(updated);
                            } catch (err) {
                              setError(
                                err instanceof Error
                                  ? err.message
                                  : "Failed to remove key"
                              );
                            } finally {
                              setRemovingKey(false);
                            }
                          }}
                          disabled={removingKey}
                          className="flex items-center gap-1 text-xs font-mono text-text-muted hover:text-red transition-colors cursor-pointer disabled:opacity-50"
                        >
                          {removingKey ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Trash2 className="w-3 h-3" />
                          )}
                          {confirmRemoveKey ? "Remove?" : "Remove key"}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Workspace */}
      <section className="mb-10">
        <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
          Workspace
        </h2>
        <div className="rounded-lg border border-border-subtle bg-surface px-4 py-3">
          <p className="text-xs text-text-muted mb-1">Path</p>
          <input
            type="text"
            defaultValue={config.workspace_path}
            key={config.workspace_path}
            onBlur={(e) => {
              const v = e.target.value.trim();
              if (v && v !== config.workspace_path) handleSave({ workspace_path: v });
            }}
            placeholder="~/anyscribe"
            spellCheck={false}
            className="w-full bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40"
          />
          <p className="text-xs text-text-muted mt-1.5 font-mono">
            {config._resolved_workspace}
          </p>
        </div>
      </section>

      <TailnetCard />

      {/* System */}
      {health && (
        <section>
          <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
            System
          </h2>
          <div className="rounded-lg border border-border-subtle bg-surface px-4 py-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-muted">Version</span>
              <span className="text-xs font-mono text-text">v{health.version}</span>
            </div>
            {Object.entries(health.dependencies).map(([dep, ok]) => (
              <div key={dep} className="flex items-center justify-between">
                <span className="text-xs text-text-muted">{dep}</span>
                <span className={`text-xs ${ok ? "text-green" : "text-red"}`}>
                  {ok ? (
                    <Check className="w-3 h-3" />
                  ) : (
                    <AlertCircle className="w-3 h-3" />
                  )}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {showSetupModal && (
        <LocalSetupModal
          onClose={() => setShowSetupModal(false)}
          onDone={async () => {
            setShowSetupModal(false);
            await refreshAll();
          }}
        />
      )}
    </div>
  );
}

// ── Local provider card ─────────────────────────────

function LocalProviderCard({
  provider,
  status,
  isExpanded,
  testResult,
  testing,
  pullingSize,
  deletingSize,
  reinstallingSize,
  config,
  onToggleExpand,
  onTest,
  onOpenSetup,
  onPull,
  onDelete,
  onReinstall,
  onDefaultChange,
  onSetLanguage,
  confirmTeardown,
  onTeardownRequest,
  onTeardownConfirm,
  onTeardownCancel,
  tearingDown,
}: {
  provider: Provider;
  status: LocalStatusResponse | null;
  isExpanded: boolean;
  testResult?: ProviderTestResult;
  testing: boolean;
  pullingSize: string | null;
  deletingSize: string | null;
  reinstallingSize: string | null;
  config: Config;
  onToggleExpand: () => void;
  onTest: () => void;
  onOpenSetup: () => void;
  onPull: (size: string) => void;
  onDelete: (size: string) => void;
  onReinstall: (size: string) => void;
  onDefaultChange: (size: string, also?: string[]) => Promise<void>;
  onSetLanguage: (code: string) => Promise<void>;
  confirmTeardown: boolean;
  onTeardownRequest: () => void;
  onTeardownConfirm: () => void;
  onTeardownCancel: () => void;
  tearingDown: boolean;
}) {
  const setUp = provider.set_up;

  return (
    <div className="rounded-lg border border-border-subtle bg-surface overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3">
        {setUp ? (
          <div className="w-2 h-2 rounded-full bg-green" />
        ) : (
          <Sparkles className="w-3.5 h-3.5 text-amber" />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-mono text-text">{provider.name}</p>
          <p className="text-xs text-text-muted truncate">
            {provider.description}
          </p>
        </div>
        {/* Always show Diagnose — runs the same structured test; pre-setup
            it surfaces which piece is missing without requiring setup. */}
        <button
          onClick={onTest}
          disabled={testing}
          className="rounded-md border border-border px-2.5 py-1 text-xs text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50"
          title={setUp ? "Run diagnostics" : "Diagnose missing dependencies"}
        >
          {testing ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : setUp ? (
            "Test"
          ) : (
            "Diagnose"
          )}
        </button>
        {testResult && (
          <span
            className={`text-xs ${
              testResult.success ? "text-green" : "text-red"
            }`}
            title={testResult.message}
          >
            {testResult.success ? (
              <Check className="w-3.5 h-3.5" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5" />
            )}
          </span>
        )}
        {!setUp ? (
          <button
            onClick={onOpenSetup}
            className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer"
          >
            Set up local transcription
          </button>
        ) : (
          <button
            onClick={onToggleExpand}
            aria-expanded={isExpanded}
            className="rounded-md border border-border px-2.5 py-1 text-xs text-text-muted hover:text-text transition-colors cursor-pointer flex items-center gap-1 whitespace-nowrap"
          >
            {isExpanded ? "Hide models" : "Manage models"}
            {isExpanded ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>
        )}
      </div>

      {/* Structured test-result sub-checks — rendered whether or not local is
          set up; pre-setup it surfaces which piece is missing. */}
      {testResult?.checks && (
        <div className="px-4 pb-3 pt-0 border-t border-border-subtle">
          <div className="mt-3 space-y-1">
            {(
              [
                ["faster-whisper", testResult.checks.faster_whisper],
                ["ffmpeg", testResult.checks.ffmpeg],
                [
                  `model: ${testResult.checks.model_cached.size ?? ""}`,
                  testResult.checks.model_cached,
                ],
              ] as const
            ).map(([label, c]) => (
              <div
                key={label}
                className="flex items-center gap-2 text-xs font-mono"
              >
                {c.ok ? (
                  <Check className="w-3 h-3 text-green shrink-0" />
                ) : (
                  <AlertCircle className="w-3 h-3 text-red shrink-0" />
                )}
                <span className="text-text-muted">{label}</span>
                <span className={c.ok ? "text-text" : "text-red"}>
                  {c.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Expanded: default-model picker, models table, teardown. */}
      {isExpanded && setUp && status && (
        <div className="px-4 pb-4 pt-0 border-t border-border-subtle">
          {/* One card per model (LocalModelPicker, shared with the setup modal
              and the wizard). Only downloaded models can become the default;
              the others offer Download in place. */}
          <div className="mt-3 mb-2 flex items-center justify-between gap-2 flex-wrap">
            <p className="text-[13px] text-text-secondary">
              Pick the model new transcripts use. Free, private, no API key. A model
              that isn't downloaded yet downloads when you pick it.
            </p>
            <span className="text-xs text-text-muted font-mono">
              {Math.round(status.total_disk_bytes / MB)} MB on disk
            </span>
          </div>
          {status.pending_default?.state === "failed" && (
            <p
              role="alert"
              className="mb-3 text-xs text-red border-l-[3px] border-red bg-red/5 rounded-md px-3 py-2"
            >
              Couldn't switch to{" "}
              {status.models.find((m) => m.size === status.pending_default?.model)?.spec
                .display_name ?? status.pending_default.model}
              : {status.pending_default.error}. Your default is still{" "}
              {status.models.find((m) => m.size === config.local_model)?.spec.display_name ??
                config.local_model}
              .
            </p>
          )}
          {status.suggestion && (
            <p className="mb-3 text-xs text-text-secondary border-l-[3px] border-blue bg-blue/[0.07] rounded-md px-3 py-2">
              {status.suggestion}
            </p>
          )}
          <LocalModelPicker
            models={status.models}
            featured={status.featured}
            languageAnswers={status.language_answers}
            caption={status.benchmark_caption}
            selected={config.local_model}
            onSelect={(id) => void onDefaultChange(id)}
            onUseSuggestion={(rec) => (rec.primary ? onDefaultChange(rec.primary, rec.also) : undefined)}
            onSetLanguage={onSetLanguage}
            renderAction={(m) => {
              const isPulling = pullingSize === m.size;
              const isDeleting = deletingSize === m.size;
              const isReinstalling = reinstallingSize === m.size;
              const isDownloading = !!m.downloading || isPulling;
              const isQueued = !!m.queued;
              const name = m.spec.display_name;
              const defaultEngine = status.models.find(
                (x) => x.size === config.local_model
              )?.spec.engine;
              const onlyDefault =
                config.local_model === m.size &&
                status.models.filter((x) => x.runnable).length === 1;
              const languageCheck = m.size === "tiny" && defaultEngine === "parakeet";
              const pending =
                status.pending_default?.state === "downloading" &&
                status.pending_default.model === m.size;
              const becomes = pending ? "; becomes your default when done" : "";
              if (isDownloading)
                return (
                  <span
                    className="text-[11px] font-mono text-amber flex items-center gap-1"
                    role="status"
                  >
                    <Loader2 className="w-3 h-3 animate-spin shrink-0" />
                    {m.progress && m.progress.total > 0
                      ? `Downloading ${m.progress.percent ?? 0}%${becomes}`
                      : `Downloading${becomes}`}
                  </span>
                );
              if (isQueued)
                return (
                  <span className="text-[11px] font-mono text-amber">
                    Waiting to download (#{m.queue_position ?? "?"}){becomes}
                  </span>
                );
              if (!m.runnable)
                return (
                  <span className="flex flex-col items-start sm:items-end gap-1">
                    {m.last_error && (
                      <span className="text-[11px] text-red">Download failed: {m.last_error}</span>
                    )}
                    <button
                      onClick={() => onPull(m.size)}
                      className="rounded-[7px] border border-dashed border-border px-2.5 py-1 text-xs text-text-secondary hover:text-text hover:bg-surface transition-colors cursor-pointer whitespace-nowrap flex items-center gap-1"
                    >
                      <Download className="w-3 h-3" />
                      {m.partial || m.cached ? "Incomplete: download again" : "Download"}
                    </button>
                  </span>
                );
              return (
                <span className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-[11px] font-mono text-green whitespace-nowrap flex items-center gap-1">
                    <Check className="w-3 h-3" />
                    downloaded{m.bytes ? ` · ${Math.round(m.bytes / MB)} MB` : ""}
                  </span>
                  <button
                    onClick={() => onReinstall(m.size)}
                    disabled={isReinstalling}
                    aria-label={`Reinstall ${name}`}
                    className="rounded-md border border-border px-1.5 py-1 text-[11px] text-text-muted hover:text-text transition-colors cursor-pointer disabled:opacity-40 flex items-center gap-1"
                  >
                    {isReinstalling ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <RefreshCw className="w-3 h-3" />
                    )}
                    Reinstall
                  </button>
                  {onlyDefault || languageCheck ? (
                    <span className="text-[10px] text-text-muted">
                      {onlyDefault ? "only downloaded model" : "needed for the language check"}
                    </span>
                  ) : (
                    <button
                      onClick={() => onDelete(m.size)}
                      disabled={isDeleting || isReinstalling}
                      aria-label={`Delete ${name}`}
                      className="rounded-md border border-border px-1.5 py-1 text-[11px] text-text-muted hover:text-red hover:border-red/30 transition-colors cursor-pointer disabled:opacity-40 flex items-center gap-1"
                    >
                      {isDeleting ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Trash2 className="w-3 h-3" />
                      )}
                      Delete
                    </button>
                  )}
                </span>
              );
            }}
          />

          <div className="mt-4 flex items-center justify-end gap-2">
            {!confirmTeardown ? (
              <button
                onClick={onTeardownRequest}
                className="text-xs text-text-muted hover:text-red transition-colors cursor-pointer font-mono"
              >
                Remove local transcription
              </button>
            ) : (
              <>
                <span className="text-xs text-text-muted font-mono">
                  Uninstall the local engines and delete all models?
                </span>
                <button
                  onClick={onTeardownCancel}
                  className="rounded-md border border-border px-2 py-1 text-xs font-mono text-text-muted hover:text-text transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={onTeardownConfirm}
                  disabled={tearingDown}
                  className="rounded-md border border-red/30 bg-red/5 px-2 py-1 text-xs font-mono text-red hover:bg-red/10 transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
                >
                  {tearingDown ? (
                    <>
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Removing…
                    </>
                  ) : (
                    "Confirm remove"
                  )}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────

/** What the next run resolves to, straight from the backend's own ladder. */
function NextRun({ resolved }: { resolved?: ResolvedRun }) {
  if (!resolved) return null;

  return (
    <div className="rounded-lg border border-border-subtle bg-surface px-4 py-3">
      <p className="text-xs font-mono text-text-muted uppercase tracking-wider mb-1.5">
        Next run
      </p>
      {resolved.error ? (
        <>
          <p className="text-base font-mono text-red">{resolved.error}</p>
          <p className="text-xs text-text-muted mt-1">fix the provider below</p>
        </>
      ) : (
        <>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-base font-mono text-text">
              {resolved.provider}
              {resolved.model ? ` · ${resolved.model}` : ""}
            </span>
            {resolved.via && (
              <span className="rounded border border-border px-1.5 py-0.5 text-[10px] font-mono text-text-muted">
                via {resolved.via}
              </span>
            )}
          </div>
          {(resolved.notes ?? []).map((note) => (
            <p
              key={note}
              className={`text-xs font-mono mt-1 whitespace-pre-line ${
                note.startsWith("WARNING:") ? "text-amber" : "text-text-muted"
              }`}
            >
              {note}
            </p>
          ))}
        </>
      )}
    </div>
  );
}

/** One row of the "what runs by default" picker: a tier, or "custom". */
function QualityChoice({
  name,
  caption,
  warn,
  muted = false,
  selected,
  disabled,
  onSelect,
}: {
  name: string;
  caption: string;
  warn: string | null;
  /** an FYI, not a problem (a local user's cloud rows) */
  muted?: boolean;
  selected: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      disabled={disabled}
      aria-pressed={selected}
      className={`w-full flex items-center gap-3 px-3 py-2 text-left border-b border-border-subtle last:border-b-0 transition-colors cursor-pointer disabled:opacity-50 ${
        selected ? "bg-amber/10" : "bg-surface hover:bg-surface-raised"
      }`}
    >
      <span
        className={`text-xs font-mono w-20 shrink-0 ${
          selected ? "text-amber" : "text-text"
        }`}
      >
        {name}
      </span>
      <span
        className={`text-xs font-mono flex-1 truncate ${
          warn ? "text-text-muted/60" : "text-text-muted"
        }`}
      >
        {caption}
      </span>
      {warn &&
        (muted ? (
          <span className="text-[11px] font-mono text-text-muted shrink-0">{warn}</span>
        ) : (
          <span className="text-[11px] font-mono text-amber flex items-center gap-1 shrink-0">
            <AlertCircle className="w-3 h-3" />
            {warn}
          </span>
        ))}
      {selected && <Check className="w-3.5 h-3.5 text-amber shrink-0" />}
    </button>
  );
}

/** User-added model slugs for an open-model provider (openrouter). */
function ExtraModels({
  provider,
  models,
  disabled,
  onChange,
}: {
  provider: string;
  models: string[];
  disabled: boolean;
  onChange: (models: string[]) => void;
}) {
  const [draft, setDraft] = useState("");
  const add = () => {
    const slug = draft.trim();
    if (!slug || models.includes(slug)) return setDraft("");
    onChange([...models, slug]);
    setDraft("");
  };

  return (
    <div className="flex items-start gap-2">
      <label className="text-xs font-mono text-text-muted w-24 shrink-0 pt-1.5">
        Custom models
      </label>
      <div className="flex-1 min-w-0">
        {models.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {models.map((m) => (
              <span
                key={m}
                className="flex items-center gap-1 rounded-md border border-border bg-surface-raised px-1.5 py-0.5 text-[11px] font-mono text-text-muted"
              >
                {m}
                <span className="text-[9px] text-amber">custom</span>
                <button
                  onClick={() => onChange(models.filter((x) => x !== m))}
                  disabled={disabled}
                  title={`Remove ${m}`}
                  className="text-text-muted hover:text-red transition-colors cursor-pointer disabled:opacity-50"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") add();
            }}
            placeholder={`e.g. vendor/model-slug for ${provider}`}
            spellCheck={false}
            className="flex-1 bg-surface-raised border border-border rounded-md px-2.5 py-1 text-xs text-text font-mono outline-none focus:border-amber/40"
          />
          <button
            onClick={add}
            disabled={disabled || !draft.trim()}
            className="rounded-md border border-border px-2 py-1 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50"
          >
            + Add model
          </button>
        </div>
      </div>
    </div>
  );
}

// A note ending in a command: keep the command on one line (it would break at its hyphens).
function NoteText({ text }: { text: string }) {
  const i = text.lastIndexOf("tailscale serve ");
  if (i < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, i)}
      <span className="whitespace-nowrap">{text.slice(i)}</span>
    </>
  );
}

function TailnetCard() {
  const { state, change } = useTailnet();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [confirmOff, setConfirmOff] = useState(false);
  const [leftThisDevice, setLeftThisDevice] = useState(false);
  const [leftNote, setLeftNote] = useState<string | null>(null);
  // A later read showing the share held again (say, turned back on at the host) ends this view.
  if (leftThisDevice && !(state?.held && !state.unknown)) {
    return (
      <section className="mb-10" id="tailnet">
        <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
          Sharing
        </h2>
        <div className="rounded-lg border border-border-subtle bg-surface px-4 py-3">
          <p className="text-xs text-text-secondary">
            Sharing is off. This device can no longer open the page. Turn it back on from
            the computer running anyscribe.
          </p>
          {leftNote && (
            <p className="text-xs text-text-muted mt-1">
              <NoteText text={leftNote} />
            </p>
          )}
        </div>
      </section>
    );
  }
  if (!state) return null;

  const flip = async () => {
    if (busy) return;
    const turningOff = state.enabled;
    if (turningOff && REMOTE && !confirmOff) {
      setConfirmOff(true);
      return;
    }
    setConfirmOff(false);
    setBusy(true);
    setErr(null);
    try {
      const next = await change(!state.enabled);
      if (turningOff && REMOTE) {
        setLeftNote(next.note);
        setLeftThisDevice(true);
      }
    } catch (e) {
      const live = e instanceof TailnetError ? e.state : undefined;
      const msg = e instanceof Error ? e.message : "Could not change tailnet sharing";
      if (live && turningOff && REMOTE && !live.held) {
        // The server says this link is refused now (a failed save still switches off first).
        setLeftNote(live.note);
        setLeftThisDevice(true);
      } else if (live) {
        setErr(msg);
      } else if (turningOff && REMOTE) {
        setErr(
          "This device lost the connection, which usually means sharing is now off. " +
            "Check on the computer running anyscribe.",
        );
      } else {
        setErr(`anyscribe couldn't confirm whether sharing changed (${msg}). Reload this page.`);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mb-10" id="tailnet">
      <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
        Sharing
      </h2>
      <div className="rounded-lg border border-border-subtle bg-surface px-4 py-3 space-y-2">
        <SettingRow label="Share on your tailnet">
          <div className="flex items-center gap-2">
            {busy && <Loader2 className="w-3.5 h-3.5 animate-spin text-text-muted" />}
            <Toggle
              value={state.enabled}
              onChange={() => void flip()}
              label="Share on your tailnet"
            />
          </div>
        </SettingRow>
        {confirmOff && (
          <div className="rounded-md border border-amber/30 bg-amber/5 px-3 py-2 space-y-2">
            <p className="text-xs text-text">
              {state.note
                ? "This device will lose the page: anyscribe will refuse this link, though your own Tailscale rule stays in place. Turn it back on from the computer running anyscribe."
                : "This device will lose the page. Turn it back on from the computer running anyscribe."}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void flip()}
                className="rounded px-3 py-2 min-h-9 text-xs bg-red/15 text-red hover:bg-red/25 cursor-pointer"
              >
                Turn off sharing
              </button>
              <button
                type="button"
                onClick={() => setConfirmOff(false)}
                className="rounded px-3 py-2 min-h-9 text-xs text-text-secondary hover:bg-surface-hover cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
        <p className="text-xs text-text-muted">
          Your tailnet is the private network of devices signed in to your
          Tailscale account. Turned on, your other computers on your tailnet can
          open this page too (it is laid out for a computer screen, not a phone).
          It is never on the public internet.
        </p>

        {busy ? (
          <p className="text-xs text-text-secondary">Asking Tailscale…</p>
        ) : state.unknown ? (
          <p className="text-xs text-text-secondary">
            anyscribe couldn't read the current sharing state.
          </p>
        ) : state.active && state.url ? (
          <div className="rounded-md border border-green/20 bg-green/5 px-3 py-2 space-y-1">
            <p className="text-xs text-green">On. Open it from your other computers on your tailnet:</p>
            <TailnetLink url={state.url} />
            {state.note && (
              <p className="text-xs text-text-muted">
                <NoteText text={state.note} />
              </p>
            )}
          </div>
        ) : state.enabled && REMOTE && state.held ? (
          // Tailscale delivered this very page, so the link works whatever the last check said.
          <div className="rounded-md border border-amber/30 bg-amber/5 px-3 py-2">
            <p className="text-xs text-amber">
              On. You're reading this over the tailnet link, so it works. anyscribe's last
              check didn't confirm it.
            </p>
          </div>
        ) : state.enabled ? (
          <div className="rounded-md border border-red/30 bg-red/5 px-3 py-2 space-y-1">
            <p className="text-xs text-red">
              {state.held
                ? "On, but the link isn't confirmed right now."
                : "On, but not working. This page is only on this computer right now."}
            </p>
            <p className="text-xs text-text-secondary">{state.reason}</p>
            <p className="text-xs text-text-secondary font-mono">
              Fix: {state.card_fix ?? state.fix}
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            <p className="text-xs text-text-secondary">
              Off. This page only answers at 127.0.0.1 or localhost on this computer.
            </p>
            {state.note && (
              <p className="text-xs text-text-muted">
                <NoteText text={state.note} />
              </p>
            )}
            {REMOTE && (
              <p className="text-xs text-amber">
                But you're viewing this through a tunnel or proxy anyscribe didn't set up. It has
                no login.
              </p>
            )}
          </div>
        )}

        {state.saved === null && !busy && (
          <p className="text-xs text-text-muted">
            Couldn't read the saved setting (config.yaml has a mistake), so this shows only
            the running dashboard.
          </p>
        )}
        {state.saved !== null && state.saved !== state.enabled && !busy && !state.unknown && (
          <p className="text-xs text-text-muted">
            Saved setting: {state.saved ? "on" : "off"}. This running dashboard:{" "}
            {state.held ? "shared" : "not shared"}. The switch changes both.
          </p>
        )}
        {err && <p className="text-xs text-red font-mono">{err}</p>}

        <p className="text-xs text-amber/80 flex gap-1.5">
          <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-px" />
          <span>
            This page has no login. Anyone on your tailnet can use it while it is
            shared: change your API keys, run transcriptions that spend your credit,
            delete transcripts, or stop it.
          </span>
        </p>
      </div>
    </section>
  );
}

function SettingRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-1">
      <label className="text-sm text-text-secondary">{label}</label>
      {children}
    </div>
  );
}

/** Green only for a key the provider accepted; amber when nothing checked it. */
function keyCheckColor(r: ProviderTestResult): string {
  if (r.checked === false) return "text-amber";
  return r.success ? "text-green" : "text-red";
}
