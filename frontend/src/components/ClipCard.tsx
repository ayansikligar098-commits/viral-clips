"use client";
import Link from "next/link";
import type { Clip } from "@/lib/types";
import { clipContextReason, clipEnd, clipHashtags, clipScore, clipStart } from "@/lib/types";import { clipCoverUrlOrNull, clipFileUrl } from "@/lib/api";
import { clipDetectedLanguage, clipSelectedHook } from "@/lib/types";

function fmt(t: number | null): string {
  if (t == null) return "—";
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function ClipCard({ clip }: { clip: Clip }) {
  const score = clipScore(clip);
  const contextReason = clipContextReason(clip);
  // Auto-generated metadata — shown only when the API returned it.
  const hook = clipSelectedHook(clip);
  const detectedLanguage = clipDetectedLanguage(clip);
  const coverUrl = clipCoverUrlOrNull(clip);
  return (
    <article className="rounded-2xl border border-white/10 bg-panel overflow-hidden">
      {coverUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={coverUrl} alt={`Cover for ${clip.title}`} className="w-full aspect-[9/16] max-h-96 object-cover bg-black" />
      ) : (
        <video src={clipFileUrl(clip)} controls playsInline preload="metadata" className="w-full h-auto aspect-[9/16] max-h-96 object-cover bg-black" />
      )}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-semibold text-white break-words min-w-0">{clip.title}</h3>
          {score != null && <span className="shrink-0 px-2 py-0.5 rounded-full bg-violet-600/20 text-violet-200 text-xs font-medium">{score}/100</span>}
        </div>
        {detectedLanguage && (
          <p className="mt-2">
            <span className="px-2 py-0.5 rounded-full bg-white/10 text-slate-200 text-xs">Language: {detectedLanguage}</span>
          </p>
        )}
        {hook && <p className="text-sm text-slate-200 mt-2">Hook: {hook}</p>}
        <p className="text-xs text-slate-400 mt-1">
          Trim {fmt(clipStart(clip))} – {fmt(clipEnd(clip))}
          {clip.duration != null ? ` · ${Math.round(clip.duration)}s` : ""}
          {clip.style || clip.editing_style ? ` · Style: ${clip.style ?? clip.editing_style}` : ""}
        </p>
        {clip.quality_gate_passed === true && <p className="text-xs text-emerald-300 mt-1">✓ Quality gate passed</p>}
        {clip.quality_gate_passed === false && (
          <p className="text-xs text-red-300 mt-1">✕ Quality gate failed{clip.quality_gate_failures?.length ? `: ${clip.quality_gate_failures.join("; ")}` : ""}</p>
        )}
        {contextReason && <p className="text-sm text-cyan-200/90 mt-2">Why selected: {contextReason}</p>}
        {clip.context_preserved === true && <p className="text-xs text-emerald-300 mt-1">✓ Context preserved</p>}
        {clip.context_preserved === false && <p className="text-xs text-amber-300 mt-1">⚠ Context not preserved</p>}
        {clipHashtags(clip).length > 0 && (
          <p className="text-xs text-slate-400 mt-2">{clipHashtags(clip).map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" ")}</p>
        )}
        <div className="flex flex-wrap gap-2 mt-4">
          <Link href={`/clips/${clip.id}`} className="inline-flex min-h-[44px] items-center px-3 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm">Open in editor</Link>
          <Link href="/scores" className="inline-flex min-h-[44px] items-center px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm">Score breakdown</Link>
          <a href={clipFileUrl(clip)} download className="inline-flex min-h-[44px] items-center px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm">Download</a>
        </div>
      </div>
    </article>
  );
}
