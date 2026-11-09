/** API client for the scribe backend. */

import type {
  Config,
  Provider,
  ProviderLanguagesResponse,
  ProviderTestResult,
  LocalStatusResponse,
  LocalModelsResponse,
  OnboardingStatus,
  OnboardingPayload,
  OnboardingResult,
  SetupLogResponse,
  TranscribeAccepted,
  TranscribeRequest,
  TranscriptMeta,
  TranscriptDetail,
  WorkspaceInfo,
} from "./types";

const BASE = "/api";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

// ── Config ───────────────────────────────────────────

export const getConfig = () => fetchJSON<Config>("/config");

export const updateConfig = (data: Partial<Config>) =>
  fetchJSON<Config>("/config", {
    method: "PUT",
    body: JSON.stringify(data),
  });

// ── Providers ────────────────────────────────────────

export const getProviders = () => fetchJSON<Provider[]>("/providers");

export const getProviderLanguages = (name: string) =>
  fetchJSON<ProviderLanguagesResponse>(`/providers/${name}/languages`);

export const testProvider = (name: string, apiKey?: string) =>
  fetchJSON<ProviderTestResult>(`/providers/${name}/test`, {
    method: "POST",
    body: apiKey ? JSON.stringify({ api_key: apiKey }) : undefined,
  });

export const getKeysStatus = () =>
  fetchJSON<Record<string, boolean>>("/keys/status");

export const updateKey = (provider_name: string, api_key: string) =>
  fetchJSON<{ success: boolean }>("/keys", {
    method: "PUT",
    body: JSON.stringify({ provider_name, api_key }),
  });

export const deleteKey = (provider_name: string) =>
  fetchJSON<{ success: boolean }>(`/keys/${provider_name}`, {
    method: "DELETE",
  });

// ── Transcription ────────────────────────────────────

export const startTranscribe = (data: TranscribeRequest) =>
  fetchJSON<TranscribeAccepted>("/transcribe", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const cancelJob = (jobId: string) =>
  fetchJSON<{ job_id: string; status: string }>(`/jobs/${jobId}/cancel`, {
    method: "POST",
  });

export const uploadFile = async (file: File): Promise<{ path: string; filename: string }> => {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
};

// ── History ──────────────────────────────────────────

export const getTranscripts = (platform?: string, limit = 50, offset = 0) => {
  const params = new URLSearchParams();
  if (platform) params.set("platform", platform);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return fetchJSON<{ items: TranscriptMeta[]; total: number; offset: number; limit: number }>(
    `/transcripts?${params}`
  );
};

export const getTranscript = (id: string) =>
  fetchJSON<TranscriptDetail>(`/transcripts/${id}`);

export const deleteTranscript = (id: string) =>
  fetchJSON<{ success: boolean; deleted: string }>(`/transcripts/${id}`, {
    method: "DELETE",
  });

export const getWorkspaceInfo = () =>
  fetchJSON<WorkspaceInfo>("/workspace/info");

// ── Health ───────────────────────────────────────────

export const getHealth = () =>
  fetchJSON<{ ok: boolean; version: string; dependencies: Record<string, boolean> }>("/health");

// ── Local transcription ──────────────────────────────

export const getLocalStatus = () =>
  fetchJSON<LocalStatusResponse>("/local/status");

export const setupLocal = (model: string) =>
  fetchJSON<{ status: string; model: string }>("/local/setup", {
    method: "POST",
    body: JSON.stringify({ model }),
  });

export const teardownLocal = () =>
  fetchJSON<{
    status: string;
    models_deleted: string[];
    bytes_freed: number;
    provider_reset: boolean;
  }>("/local/teardown", { method: "POST" });

// ── Local model cache ────────────────────────────────

export const listLocalModels = () =>
  fetchJSON<LocalModelsResponse>("/models/local");

export const pullLocalModel = (size: string) =>
  fetchJSON<{ status: string; size: string }>(`/models/local/${size}/pull`, {
    method: "POST",
  });

export const deleteLocalModel = (size: string) =>
  fetchJSON<{ status: string; size: string; bytes_freed: number }>(
    `/models/local/${size}`,
    { method: "DELETE" }
  );

export const reinstallLocalModel = (size: string) =>
  fetchJSON<{
    status: string;
    size: string;
    bytes_freed: number;
    bytes_downloaded: number;
  }>(`/models/local/${size}/reinstall`, { method: "POST" });

export const getSetupLog = (since: number) =>
  fetchJSON<SetupLogResponse>(`/local/setup/log?since=${since}`);

// ── Onboarding ───────────────────────────────────────

export const getOnboardingStatus = () =>
  fetchJSON<OnboardingStatus>("/onboarding/status");

export const saveOnboarding = (payload: OnboardingPayload) =>
  fetchJSON<OnboardingResult>("/onboarding/save", {
    method: "POST",
    body: JSON.stringify(payload),
  });

// ── System ───────────────────────────────────────────

export type AutostartState = { supported: boolean; enabled: boolean };

export const getAutostart = () => fetchJSON<AutostartState>("/autostart");

export const setAutostart = (enabled: boolean) =>
  fetchJSON<AutostartState>("/autostart", {
    method: "PUT",
    body: JSON.stringify({ enabled }),
  });

/** Live tailnet sharing of this server; `saved` is the setting (differs after --tailnet/--local-only). */
export type TailnetState = {
  enabled: boolean;
  active: boolean;
  url: string | null;
  reason: string | null;
  fix: string | null;
  card_fix: string | null;
  note: string | null;
  held: boolean; // the tailnet name is answered (the gate); the display may read failed meanwhile
  saved: boolean | null; // null: config.yaml could not be read
  unknown?: boolean; // client only: a toggle failed and the live state couldn't be read back
};

/** A failed toggle; `state` is the server's live state when it could say. */
export class TailnetError extends Error {
  state?: TailnetState;
  constructor(message: string, state?: TailnetState) {
    super(message);
    this.state = state;
  }
}

export const getTailnet = () => fetchJSON<TailnetState>("/tailnet");

export const setTailnet = async (enabled: boolean): Promise<TailnetState> => {
  const res = await fetch(`${BASE}/tailnet`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (res.ok) return res.json();
  const body = await res.json().catch(() => null);
  throw new TailnetError(`${res.status}: ${body?.detail ?? res.statusText}`, body?.state);
};
