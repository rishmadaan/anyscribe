/** TypeScript interfaces matching the Python Pydantic models. */

/** GET/PUT /api/config `_resolved` — what the next run will actually use.
 *  Either the resolved plan, or `error` when the config can't resolve. */
export interface ResolvedRun {
  provider?: string;
  model?: string | null;
  via?: string; // "flag" | "diarize" | "quality: <tier>" | "config"
  notes?: string[]; // a note starting with "WARNING:" renders amber
  error?: string;
}

export interface Config {
  provider: string;
  quality: string;
  language: string;
  keep_media: boolean;
  output_format: string;
  diarize: boolean;
  prompt_download: string;
  local_file_media: string;
  workspace_path: string;
  local_model: string;
  provider_models: Record<string, string>;
  extra_models: Record<string, string[]>;
  instagram: { browser: string };
  _resolved_workspace?: string;
  _quality_tiers?: Record<string, string>; // tier -> provider it resolves to
  _resolved?: ResolvedRun;
}

export interface Provider {
  name: string;
  description: string;
  has_key: boolean;
  set_up: boolean;
  key_in_env_file?: boolean; // key is saved in .env (removable), not just inherited
  key_url?: string;
  models: string[]; // pickable model ids; first is the provider default
  freeform_model: boolean; // any slug is valid (openrouter) → text input, not select
}

/** One local model's measured figures (providers/local_models.py MODEL_SPECS). */
export interface ModelSpec {
  display_name: string;
  engine: "whisper" | "parakeet";
  accuracy: number; // 1-5
  speed: number; // 1-5
  min_per_hour: number; // minutes to transcribe 1 hour of audio on the reference machine
  download_mb: number;
  ram_mb: number;
  languages: string;
  language_codes: string[] | null;
  use_for: string;
  featured: number | null; // card order, null = under "More models"
  badge: string | null;
  tucked: string | null; // why it sits under "More models"
}

/** GET /api/local/recommend — the "Help me choose" answer. */
export interface LocalRecommendation {
  answer: string;
  /** null when nothing fits on disk (the reason says how much is needed) */
  primary: string | null;
  also: string[];
  reasons: string[];
  download_mb: number;
  /** a language worth offering to set (Hindi answer), else null */
  set_language: string | null;
}

/** GET /api/local/registry — the model registry, no disk scan. */
export interface LocalRegistry {
  recommended_model: string;
  featured: string[];
  specs: Record<string, ModelSpec>;
  benchmark_caption: string;
}

export interface DownloadProgress {
  downloaded: number;
  total: number;
  percent: number | null;
}

export interface LocalModelEntry {
  size: string;
  /** the model's own files are complete (sizes and disk maths only) */
  cached: boolean;
  /** some bytes on disk but not complete (interrupted download); pull resumes it */
  partial?: boolean;
  /** can transcribe now: engine installed, files complete, Parakeet's helpers too */
  runnable: boolean;
  bytes: number;
  repo: string;
  spec: ModelSpec;
  downloading?: boolean;
  queued?: boolean;
  queue_position?: number;
  progress?: DownloadProgress | null;
  error?: string | null;
  last_error?: string | null;
}

export interface LocalStatusResponse {
  set_up: boolean;
  faster_whisper_installed: boolean;
  faster_whisper_version: string | null;
  ffmpeg_ok: boolean;
  ffmpeg_message: string;
  default_model: string;
  models: LocalModelEntry[];
  total_disk_bytes: number;
  install_method: string;
  setup_running: boolean;
  setup_phase: string | null;
  setup_error: string | null;
  setup_last_model: string | null;
  setup_progress: DownloadProgress | null;
  recommended_model: string;
  choices: string[];
  featured: string[];
  language_answers: Record<string, string>;
  onnx_asr_installed: boolean;
  runtime_ready: boolean;
  /** setup replaced an engine the server had loaded: restart anyscribe */
  restart_needed: boolean;
  benchmark_caption: string;
  suggestion: string | null;
  /** extra models the last setup downloads afterwards (Turbo for a mix) */
  setup_also: string[];
  /** how to make local the default for every run; null when it already is */
  use_local_tip: string | null;
  /** a chosen model that becomes the default once it can run (server-owned) */
  pending_default: PendingDefault | null;
}

export interface PendingDefault {
  model: string;
  also: string[];
  state: "downloading" | "failed";
  error: string | null;
}

export interface LocalModelsResponse {
  default: string;
  faster_whisper_installed: boolean;
  total_disk_bytes: number;
  models: LocalModelEntry[];
  queue?: string[];
}

export interface OnboardingStatus {
  completed: boolean;
  has_workspace: boolean;
  has_any_api_key: boolean;
  local_ready: boolean;
  provider_keys: Record<string, boolean>;
  current_provider: string;
  recommended_next_step: string;
}

export interface OnboardingPayload {
  provider: string;
  api_key?: string;
  workspace?: string;
  language?: string;
  keep_media?: boolean;
  output_format?: string;
  local_model?: string;
  extra_api_keys?: Record<string, string>;
  instagram_browser?: string;
}

export interface OnboardingResult {
  status: "onboarded" | "partial";
  provider: string;
  workspace: string;
  local_enabled: boolean;
  api_keys_set: string[];
  skill_installed: boolean;
  local_setup: unknown;
  config_file: string;
}

export interface SetupLogResponse {
  lines: string[];
  total: number;
  running: boolean;
}

export interface ProviderTestCheck {
  ok: boolean;
  message: string;
  size?: string;
}

export interface ProviderTestResult {
  success: boolean;
  /** false: nothing confirmed or refused the key (Sarvam, or provider unreachable) */
  checked?: boolean;
  message: string;
  checks?: {
    faster_whisper: ProviderTestCheck;
    ffmpeg: ProviderTestCheck;
    model_cached: ProviderTestCheck;
  };
}

export interface LanguageOption {
  code: string;
  name: string;
}

export interface ProviderLanguagesResponse {
  languages: LanguageOption[];
  freeform: boolean;
}

export interface TranscribeRequest {
  url: string;
  provider?: string;
  model?: string;
  quality?: string;
  language?: string;
  diarize?: boolean;
  keep_media?: boolean;
  output_format?: string;
  force?: boolean;
}

export interface ProgressEvent {
  step: string;   // download, transcribe, write, index, done, error
  status: string;  // started, completed, error
  message: string;
  percent?: number;
  data?: Record<string, unknown>;
}

export interface TranscriptMeta {
  id: string;
  title: string;
  date: string;
  platform: string;
  duration: string;
  language: string;
  word_count: number;
  provider: string;
  source_url: string;
  file_path: string;
  diarized: boolean;
}

export interface TranscriptDetail {
  id: string;
  frontmatter: Record<string, unknown>;
  body: string;
  file_path: string;
}

export interface JobResult {
  file_path: string;
  title: string;
  platform: string;
  duration: string;
  language: string;
  word_count: number;
  provider: string;
  model?: string;
  notes?: string[]; // run-time switches, e.g. the Parakeet language guard
  cached?: boolean;
}

/** POST /api/transcribe — the resolved plan for this run. */
export interface TranscribeAccepted {
  job_id: string;
  provider: string;
  model: string | null;
  notes: string[];
}

export interface WorkspaceInfo {
  path: string;
  file_count: number;
  total_words: number;
}
