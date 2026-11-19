import type { Config, LocalModelEntry, Provider } from "./types";

/** Default model for a provider: the pinned one, else the provider's first. */
export function defaultModelFor(
  provider: Provider | undefined,
  pinned: Record<string, string> | undefined
): string {
  if (!provider) return "";
  return (pinned ?? {})[provider.name] ?? provider.models?.[0] ?? "";
}

/**
 * What a quality tier resolves to right now, e.g. "deepgram · nova-3".
 * `local` has no model list — its choice lives in config.local_model.
 */
export function tierSummary(
  tier: string,
  config: Config,
  providers: Provider[]
): { provider: string; model: string; hasKey: boolean } {
  const name = (config._quality_tiers ?? {})[tier] ?? "";
  const p = providers.find((x) => x.name === name);
  return {
    provider: name,
    model:
      name === "local" ? config.local_model : defaultModelFor(p, config.provider_models),
    // Providers not loaded yet → assume fine, so no false "needs API key".
    hasKey: p ? p.has_key : true,
  };
}

/** User-added model slugs for a provider (openrouter only, by design). */
export function extraModelsFor(config: Config, provider: string): string[] {
  return (config.extra_models ?? {})[provider] ?? [];
}

/** Local-model sizes from the registry, in the units the cards show. */
export function formatMB(mb: number): string {
  if (mb < 1000) return `${mb} MB`;
  return `${(mb / 1000).toFixed(1).replace(/\.0$/, "")} GB`;
}

export function formatPerHour(min: number): string {
  if (min < 90) return `${min} min`;
  return `${(min / 60).toFixed(1).replace(/\.0$/, "")} hours`;
}

/** MB still to download for ``ids`` (plus the Tiny language check when one is
 * Parakeet): weights not yet on disk, so a half-done download counts in full. */
export function downloadMbFor(models: LocalModelEntry[], ids: string[]): number {
  const byId = Object.fromEntries(models.map((m) => [m.size, m]));
  const need = new Set(ids.filter((id) => byId[id] && !byId[id].cached));
  if (ids.some((id) => byId[id]?.spec.engine === "parakeet") && byId["tiny"] && !byId["tiny"].cached)
    need.add("tiny");
  return [...need].reduce((n, id) => n + byId[id].spec.download_mb, 0);
}
