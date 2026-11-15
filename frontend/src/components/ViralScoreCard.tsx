"use client";
import { clipCoverUrlOrNull } from "@/lib/api";
import type { Clip } from "@/lib/types";
import { SCORE_FACTOR_LABELS, SCORE_FACTOR_MAX, clipContextReason, clipDetectedLanguage, clipScore, clipSelectedHook } from "@/lib/types";

// Never show a bare score: every score is shown with its per-factor
// breakdown + reasons and the quality-gate status. If the backend did not
// return a breakdown, that is stated instead of inventing reasons.
export default function ViralScoreCard({ clip }: { clip: Clip }) {
  const score = clipScore(clip);
  const breakdown = clip.score_breakdown ?? null;
  const entries = breakdown ? Object.entries(breakdown) : [];
  const gate = clip.quality_gate_passed;
  const contextReason = clipContextReason(clip);
  // Auto-generated metadata — shown only when the API returned it.
  const hook = clipSelectedHook(clip);
  const detectedLanguage = clipDetectedLanguage(clip);
  const coverUrl = clipCoverUrlOrNull(clip);
  return (
    <div className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 min-w-0">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">Viral score</p>
          <p className="text-3xl sm:text-4xl font-bold text-white mt-1 break-words">
            {score != null ? `${score} / 100` : "Not scored yet"}
          </p>
          {score == null && <p className="text-sm text-slate-400 mt-1">The backend has not scored this clip yet.</p>}
        </div>
        {gate === true && (
          <span className="shrink-0 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-300">✓ Quality gate passed</span>
        )}
        {gate === false && (
          <span className="shrink-0 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-300">✕ Quality gate failed</span>
        )}
        {gate == null && (
          <span className="shrink-0 px-2.5 py-1 rounded-full text-xs font-medium bg-white/10 text-slate-300">Quality gate: not reported</span>
        )}
      </div>

      {/* Auto-generated title / hook / language / cover — API only. */}
      {(coverUrl || hook || detectedLanguage || clip.title) && (
        <div className="mt-4 flex gap-3">
          {coverUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={coverUrl} alt={`Cover for ${clip.title}`} className="w-16 shrink-0 aspect-[9/16] object-cover bg-black rounded-lg border border-white/10" />
          )}
          <div className="min-w-0">
            {clip.title && <p className="text-sm font-medium text-white truncate">{clip.title}</p>}
            {hook && <p className="text-sm text-slate-300 mt-1">Hook: {hook}</p>}
            {detectedLanguage && (
              <p className="mt-2">
                <span className="px-2 py-0.5 rounded-full bg-white/10 text-slate-200 text-xs">Language: {detectedLanguage}</span>
              </p>
            )}
          </div>
        </div>
      )}

      {clip.quality_gate_failures && clip.quality_gate_failures.length > 0 && (
        <div className="mt-3 rounded-lg bg-red-500/10 border border-red-500/30 p-3">
          <p className="text-sm font-medium text-red-300">Why it failed the quality gate:</p>
          <ul className="list-disc list-inside text-sm text-red-200 mt-1">
            {clip.quality_gate_failures.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}

      {/* Context-aware highlight: API-provided only, omitted when absent. */}
      {contextReason && (
        <div className="mt-3 rounded-lg bg-cyan-500/10 border border-cyan-500/30 p-3">
          <p className="text-sm font-medium text-cyan-200">Why this moment was selected</p>
          <p className="text-sm text-cyan-100/90 mt-1">{contextReason}</p>
        </div>
      )}
      {clip.context_preserved === true && (
        <p className="mt-2 text-xs text-emerald-300">✓ Context preserved — setup and payoff kept together.</p>
      )}
      {clip.context_preserved === false && (
        <p className="mt-2 text-xs text-amber-300">⚠ Context not preserved — this cut may lose its setup or payoff.</p>
      )}

      <div className="mt-4 space-y-3">
        {entries.length === 0 && (
          <p className="text-sm text-slate-400">No score breakdown returned by the API yet — no reasons invented here.</p>
        )}
        {entries.map(([key, factor]) => {
          if (!factor) return null;
          const max = factor.max ?? SCORE_FACTOR_MAX[key] ?? 0;
          const pct = max > 0 ? Math.min(100, Math.round((factor.score / max) * 100)) : 0;
          return (
            <div key={key}>
              <div className="flex justify-between text-sm">
                <span className="text-slate-200">{SCORE_FACTOR_LABELS[key] ?? key}</span>
                <span className="text-slate-400">{factor.score}{max ? ` / ${max}` : ""}</span>
              </div>
              <div className="h-2 bg-white/10 rounded-full mt-1 overflow-hidden">
                <div className="h-full bg-violet-500 rounded-full" style={{ width: `${pct}%` }} />
              </div>
              {factor.reason && <p className="text-xs text-slate-400 mt-1">{factor.reason}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
