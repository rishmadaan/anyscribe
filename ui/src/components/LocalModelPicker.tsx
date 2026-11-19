/** The one local-model picker, used in Settings, the setup modal and the
 * first-run wizard. Every figure comes from the backend registry
 * (providers/local_models.py); nothing about a model is hard-coded here.
 *
 * Featured models are radio cards; the rest sit under "More models" with the
 * reason they're tucked away. "Help me choose" asks one question and shows
 * the backend's recommendation in plain sentences. Only the reply to the
 * latest question (asked after the latest card click) counts. In the wizard
 * and setup modal it moves the selection (nothing commits until their setup
 * button); in Settings (``onUseSuggestion``) it only suggests, and one button
 * commits.
 */

import { useRef, useState, type KeyboardEvent, type MutableRefObject, type ReactNode } from "react";
import { Check, Loader2, Sparkles } from "lucide-react";
import { recommendLocal } from "../api/client";
import { formatMB, formatPerHour } from "../api/models";
import type { LocalModelEntry, LocalRecommendation } from "../api/types";

interface Props {
  models: LocalModelEntry[];
  featured: string[];
  languageAnswers: Record<string, string>;
  /** Where the measured figures come from; shown under the cards. */
  caption: string;
  selected: string | null;
  /** Called for any card the person clicks, downloaded or not; the caller
   * decides what a click on a not-downloaded model does. */
  onSelect: (id: string) => void;
  /** Right-hand status / actions for a model; defaults to plain status text. */
  renderAction?: (m: LocalModelEntry) => ReactNode;
  /** Called with every current "Help me choose" result, including "nothing
   * fits" (primary null): the caller moves its selection to the primary. */
  onRecommendation?: (rec: LocalRecommendation) => void;
  /** Settings: an answer only highlights the suggestion; this button commits. */
  onUseSuggestion?: (rec: LocalRecommendation) => void;
  /** Offered when the suggestion carries a language worth setting (Hindi). */
  onSetLanguage?: (code: string) => Promise<void> | void;
  disabled?: boolean;
  /** Open "Help me choose" from the start (first-run setup). */
  guideOpen?: boolean;
}

function Dots({ n }: { n: number }) {
  return (
    <span className="inline-flex gap-[3px]" aria-hidden="true">
      {[1, 2, 3, 4, 5].map((i) => (
        <i
          key={i}
          className={`block w-[7px] h-[7px] rounded-full ${i <= n ? "bg-text" : "bg-border"}`}
        />
      ))}
    </span>
  );
}

function Rating({ label, n }: { label: string; n: number }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      {label} <Dots n={n} />{" "}
      <b className="font-mono font-medium text-text">{n}/5</b>
    </span>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <span>
      {label} <b className="font-mono font-medium text-text">{value}</b>
    </span>
  );
}

const MB = 1024 * 1024;

function DefaultStatus({ m }: { m: LocalModelEntry }) {
  if (m.runnable)
    return (
      <span className="text-[11px] font-mono text-green whitespace-nowrap flex items-center gap-1">
        <Check className="w-3 h-3" /> downloaded{m.bytes ? ` · ${Math.round(m.bytes / MB)} MB` : ""}
      </span>
    );
  return (
    <span className="text-[11px] font-mono text-text-muted whitespace-nowrap">
      {m.cached ? "downloaded; setup finishes it" : m.partial ? "incomplete: the download resumes" : "not downloaded"}
    </span>
  );
}

export default function LocalModelPicker({
  models,
  featured,
  languageAnswers,
  caption,
  selected,
  onSelect,
  renderAction,
  onRecommendation,
  onUseSuggestion,
  onSetLanguage,
  disabled = false,
  guideOpen = false,
}: Props) {
  // Bumped by every question and every card click: a reply counts only if
  // nothing came after its question.
  const seqRef = useRef(0);
  const [suggestion, setSuggestion] = useState<LocalRecommendation | null>(null);
  const suggested = onUseSuggestion && suggestion?.primary ? [suggestion.primary, ...suggestion.also] : [];
  const byId = Object.fromEntries(models.map((m) => [m.size, m]));
  const cards = featured.map((id) => byId[id]).filter(Boolean);
  const rest = models.filter((m) => !featured.includes(m.size));
  const selectedModel = selected ? byId[selected] : undefined;
  const checker = byId["tiny"];

  const canSelect = () => !disabled;
  const status = (m: LocalModelEntry) => (renderAction ? renderAction(m) : <DefaultStatus m={m} />);

  const pick = (id: string) => {
    seqRef.current++;
    onSelect(id);
  };
  const onKey = (e: KeyboardEvent, m: LocalModelEntry) => {
    if ((e.key === " " || e.key === "Enter") && canSelect()) {
      e.preventDefault();
      pick(m.size);
    }
  };

  return (
    <div>
      <HelpMeChoose
        answers={languageAnswers}
        disabled={disabled}
        nameOf={(id) => byId[id]?.spec.display_name ?? id}
        startOpen={guideOpen}
        seqRef={seqRef}
        models={models}
        current={selected}
        onUse={(rec) => {
          setSuggestion(rec);
          if (!onUseSuggestion) onRecommendation?.(rec);
        }}
        onUseSuggestion={onUseSuggestion}
        onSetLanguage={onSetLanguage}
      />

      <div className="grid gap-2.5" role="radiogroup" aria-label="Local model">
        {cards.map((m) => {
          const checked = selected === m.size;
          const isSuggested = suggested.includes(m.size);
          const selectable = canSelect();
          return (
            // The radio is the left part only: the actions on the right are
            // its siblings, so a not-yet-downloaded (aria-disabled) model's
            // Download button stays enabled for assistive tech.
            <div
              key={m.size}
              onClick={() => selectable && pick(m.size)}
              data-suggested={isSuggested || undefined}
              className={`grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-x-3 gap-y-2 items-start p-3.5 rounded-[10px] border text-left transition-colors ${
                checked
                  ? "border-amber bg-amber/[0.06]"
                  : isSuggested
                    ? "border-blue border-dashed bg-blue/[0.05]"
                    : "border-border-subtle bg-surface-raised hover:bg-surface-hover"
              } ${selectable ? "cursor-pointer" : "cursor-default"}`}
            >
              <div
                role="radio"
                aria-checked={checked}
                aria-disabled={!selectable}
                tabIndex={selectable ? 0 : -1}
                onKeyDown={(e) => onKey(e, m)}
                data-model={m.size}
                className="grid grid-cols-[22px_1fr] gap-x-3 items-start rounded-md outline-none focus-visible:ring-2 focus-visible:ring-amber/60"
              >
                <span
                  className={`mt-[3px] w-4 h-4 rounded-full border-2 ${
                    checked
                      ? "border-amber bg-amber shadow-[inset_0_0_0_3px_var(--color-surface-raised)]"
                      : "border-text-muted"
                  }`}
                  aria-hidden="true"
                />
                <span className="min-w-0">
                  <span className="font-semibold text-text flex flex-wrap items-center gap-2">
                    {m.spec.display_name}
                    {m.spec.badge && (
                      <span
                        className={`text-[10px] font-mono font-medium px-[7px] py-[2px] rounded-[5px] ${
                          m.spec.badge === "recommended"
                            ? "bg-amber-dim text-amber"
                            : "bg-blue/15 text-blue"
                        }`}
                      >
                        {m.spec.badge}
                      </span>
                    )}
                    {isSuggested && (
                      <span className="text-[10px] font-mono font-medium px-[7px] py-[2px] rounded-[5px] bg-blue/15 text-blue">
                        Suggested
                      </span>
                    )}
                  </span>
                  <span className="block text-[13px] text-text-secondary mt-0.5">
                    {m.spec.use_for}
                  </span>
                  <span className="flex flex-wrap gap-x-[18px] gap-y-1.5 mt-2.5 text-xs text-text-secondary">
                    <Rating label="Accuracy" n={m.spec.accuracy} />
                    <Rating label="Speed" n={m.spec.speed} />
                    <Fact label="1 hour of audio ≈" value={formatPerHour(m.spec.min_per_hour)} />
                    {/* one size per card: the disk size shows once downloaded */}
                    {!m.cached && <Fact label="Download" value={formatMB(m.spec.download_mb)} />}
                    <Fact label="Memory" value={formatMB(m.spec.ram_mb)} />
                  </span>
                </span>
              </div>
              <span
                className="pl-[34px] sm:pl-0 sm:justify-self-end"
                onClick={(e) => e.stopPropagation()}
              >
                {status(m)}
              </span>
            </div>
          );
        })}
      </div>

      <p className="mt-2.5 text-[11px] text-text-muted" data-testid="benchmark-caption">
        {caption}
      </p>

      {selectedModel?.spec.engine === "parakeet" && (
        <div className="mt-3.5 px-3.5 py-3 rounded-[10px] border border-border-subtle bg-surface-raised text-[13px] text-text-secondary">
          <b className="text-text">Language check is on.</b> Before using Parakeet,
          anyscribe checks the language at the start, middle and end of each recording
          (speech only, a few seconds, using a 75 MB helper, Whisper Tiny
          {checker ? (checker.runnable ? ", which is downloaded" : ", which downloads with Parakeet") : ""}
          ). If any of them isn't one of {selectedModel.spec.display_name}'s{" "}
          {selectedModel.spec.language_codes?.length ?? 0} languages, it uses Whisper
          Large v3 Turbo (or the best other Whisper model you have) instead and says so
          on the transcript. If no Whisper model is downloaded, it stops and says what
          to download.
        </div>
      )}

      {rest.length > 0 && (
        <details className="mt-3 border-t border-border-subtle pt-2.5">
          <summary className="cursor-pointer text-[13px] text-text-secondary">
            More models ({rest.length}) — older or slower options
          </summary>
          <div className="overflow-x-auto mt-2.5">
            <table className="w-full border-collapse text-xs min-w-[560px]">
              <thead>
                <tr className="text-left text-text-muted">
                  <th className="font-medium p-1.5 border-b border-border-subtle">Use</th>
                  <th className="font-medium p-1.5 border-b border-border-subtle">Model</th>
                  <th className="font-medium p-1.5 border-b border-border-subtle">Accuracy</th>
                  <th className="font-medium p-1.5 border-b border-border-subtle">Speed</th>
                  <th className="font-medium p-1.5 border-b border-border-subtle">1 hour of audio</th>
                  <th className="font-medium p-1.5 border-b border-border-subtle">
                    Why it's tucked away
                  </th>
                  <th className="font-medium p-1.5 border-b border-border-subtle">Status</th>
                </tr>
              </thead>
              <tbody className="text-text-secondary">
                {rest.map((m) => (
                  <tr key={m.size} data-model={m.size}>
                    <td className="p-1.5 border-b border-border-subtle">
                      <input
                        type="radio"
                        name="local-model-more"
                        aria-label={`Use ${m.spec.display_name}`}
                        checked={selected === m.size}
                        disabled={!canSelect()}
                        onChange={() => pick(m.size)}
                        className="accent-amber cursor-pointer disabled:cursor-default"
                      />
                    </td>
                    <td className="p-1.5 border-b border-border-subtle text-text">
                      {m.spec.display_name}
                    </td>
                    <td className="p-1.5 border-b border-border-subtle font-mono text-text">
                      {m.spec.accuracy}/5
                    </td>
                    <td className="p-1.5 border-b border-border-subtle font-mono text-text">
                      {m.spec.speed}/5
                    </td>
                    <td className="p-1.5 border-b border-border-subtle font-mono text-text">
                      ~{formatPerHour(m.spec.min_per_hour)}
                    </td>
                    <td className="p-1.5 border-b border-border-subtle">{m.spec.tucked}</td>
                    <td className="p-1.5 border-b border-border-subtle">{status(m)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}

function HelpMeChoose({
  answers,
  disabled,
  nameOf: name,
  startOpen,
  seqRef,
  models,
  current,
  onUse,
  onUseSuggestion,
  onSetLanguage,
}: {
  answers: Record<string, string>;
  disabled: boolean;
  nameOf: (id: string) => string;
  startOpen: boolean;
  seqRef: MutableRefObject<number>;
  models: LocalModelEntry[];
  /** the current default (Settings); a suggestion of it offers no Use button */
  current: string | null;
  onUse: (rec: LocalRecommendation) => void;
  onUseSuggestion?: (rec: LocalRecommendation) => void;
  onSetLanguage?: (code: string) => Promise<void> | void;
}) {
  const [open, setOpen] = useState(startOpen);
  const [answer, setAnswer] = useState<string | null>(null);
  const [rec, setRec] = useState<LocalRecommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [languageSet, setLanguageSet] = useState(false);
  const [using, setUsing] = useState(false);
  // Requests still out; the spinner shows while any is.
  const inFlight = useRef(0);
  const [loading, setLoading] = useState(false);

  const ask = async (key: string) => {
    const mine = ++seqRef.current;
    setAnswer(key);
    setRec(null);
    setLanguageSet(false);
    setError(null);
    inFlight.current++;
    setLoading(true);
    try {
      const r = await recommendLocal(key);
      if (mine !== seqRef.current) return; // a later answer or card click replaced it
      setRec(r);
      onUse(r);
    } catch (e) {
      if (mine === seqRef.current)
        setError(e instanceof Error ? e.message : "Couldn't get a suggestion");
    } finally {
      inFlight.current--;
      setLoading(inFlight.current > 0);
    }
  };

  const use = async (r: LocalRecommendation) => {
    setUsing(true);
    try {
      await onUseSuggestion?.(r);
    } finally {
      setUsing(false);
    }
  };
  const allRunnable =
    !!rec?.primary &&
    [rec.primary, ...rec.also].every((id) => models.find((m) => m.size === id)?.runnable);

  const setLanguage = async (code: string) => {
    try {
      await onSetLanguage?.(code);
      setLanguageSet(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't set the language");
    }
  };

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        disabled={disabled}
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-text-secondary hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50"
      >
        <Sparkles className="w-3.5 h-3.5 text-amber" />
        {open ? "Hide the guide" : "Help me choose"}
      </button>
      {open && (
        <div className="mt-2.5 rounded-[10px] border border-border-subtle bg-surface-raised p-3.5">
          <p className="text-sm text-text font-medium mb-2" id="help-q">
            What language is most of your audio?
          </p>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-labelledby="help-q">
            {Object.entries(answers).map(([key, label]) => (
              <button
                key={key}
                type="button"
                role="radio"
                aria-checked={answer === key}
                disabled={disabled}
                onClick={() => ask(key)}
                className={`rounded-md border px-2.5 py-1.5 text-xs transition-colors cursor-pointer disabled:opacity-50 ${
                  answer === key
                    ? "border-amber text-amber bg-amber/[0.08]"
                    : "border-border text-text-secondary hover:text-text"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          {loading && (
            <p className="mt-3 text-xs text-text-muted flex items-center gap-1.5">
              <Loader2 className="w-3 h-3 animate-spin" /> Checking this computer…
            </p>
          )}
          {error && <p className="mt-3 text-xs text-red font-mono">{error}</p>}
          {rec && (
            <div
              className={`mt-3 border-l-[3px] rounded-md px-3 py-2.5 ${
                rec.primary ? "border-blue bg-blue/[0.07]" : "border-red bg-red/5"
              }`}
            >
              <p className="text-[13px] text-text font-medium" data-testid="recommendation">
                {rec.primary ? (
                  <>
                    {onUseSuggestion ? "Suggested" : "Selected"}:{" "}
                    <span data-pick={rec.primary}>{name(rec.primary)}</span>
                    {rec.also.length > 0 && <> + {rec.also.map(name).join(", ")}</>}
                  </>
                ) : (
                  "Not enough disk space"
                )}
              </p>
              {rec.reasons.map((r) => (
                <p key={r} className="text-[13px] text-text-secondary mt-1">
                  {r}
                </p>
              ))}
              {rec.primary && onUseSuggestion && allRunnable && rec.primary === current && (
                <p className="mt-2.5 text-xs text-green flex items-center gap-1">
                  <Check className="w-3 h-3" /> This is already your default
                </p>
              )}
              {rec.primary && onUseSuggestion && !(allRunnable && rec.primary === current) && (
                <button
                  type="button"
                  onClick={() => use(rec)}
                  disabled={using || disabled}
                  className="mt-2.5 rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer disabled:opacity-50"
                >
                  Use {[rec.primary, ...rec.also].map(name).join(" + ")}
                  {allRunnable
                    ? " (already downloaded)"
                    : rec.download_mb > 0
                      ? ` (downloads ${formatMB(rec.download_mb)})`
                      : " (finishes its download)"}
                </button>
              )}
              {rec.set_language && onSetLanguage && (
                <div className="mt-2.5 flex flex-wrap items-center gap-2">
                  {languageSet ? (
                    <span className="text-xs text-green flex items-center gap-1">
                      <Check className="w-3 h-3" /> Language set to Hindi
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setLanguage(rec.set_language!)}
                      className="rounded-md border border-amber text-amber px-3 py-1.5 text-xs hover:bg-amber/10 transition-colors cursor-pointer"
                    >
                      My audio is Hindi: set language to Hindi
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
