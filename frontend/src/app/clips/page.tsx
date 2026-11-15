"use client";
import { useEffect, useState } from "react";
import Topbar from "@/components/Topbar";
import ClipCard from "@/components/ClipCard";
import EmptyState from "@/components/EmptyState";
import { listClips } from "@/lib/api";
import { clipScore } from "@/lib/types";
import type { Clip } from "@/lib/types";

export default function ClipsPage() {
  const [clips, setClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [onlyPassed, setOnlyPassed] = useState(false);

  useEffect(() => {
    listClips()
      .then((c) => setClips([...c].sort((a, b) => (clipScore(b) ?? -1) - (clipScore(a) ?? -1))))
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load clips."))
      .finally(() => setLoading(false));
  }, []);

  const shown = onlyPassed ? clips.filter((c) => c.quality_gate_passed === true) : clips;
  const passedCount = clips.filter((c) => c.quality_gate_passed === true).length;

  return (
    <>
      <Topbar title="Generated Clips" />
      <main className="p-4 sm:p-6 space-y-4 min-w-0">
        <p className="text-slate-400 text-sm">
          Fewer, better clips: the pipeline returns 3–5 strong clips per video, ranked by viral score.
          {clips.length > 0 && ` ${passedCount} of ${clips.length} passed the quality gate.`}
        </p>
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input type="checkbox" checked={onlyPassed} onChange={(e) => setOnlyPassed(e.target.checked)} />
          Show only quality-gate passed clips
        </label>
        {loading && <p className="text-slate-400">Loading clips…</p>}
        {error && <p className="text-sm text-red-300">{error}</p>}
        {!loading && !error && clips.length === 0 && (
          <EmptyState title="No clips yet" message="Upload a video and run analysis. The pipeline will return 3–5 strong, quality-gated clips — not 10–20 random cuts." actionHref="/upload" actionLabel="Upload a video" />
        )}
        {!loading && !error && clips.length > 0 && shown.length === 0 && (
          <EmptyState title="No clips passed the gate" message="Clips were generated but none passed the quality gate yet. Check the Viral Score page for the failure reasons." actionHref="/scores" actionLabel="View scores" />
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {shown.map((c) => <ClipCard key={String(c.id)} clip={c} />)}
        </div>
      </main>
    </>
  );
}
