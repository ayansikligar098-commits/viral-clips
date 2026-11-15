"use client";
import { useEffect, useState } from "react";
import Topbar from "@/components/Topbar";
import ViralScoreCard from "@/components/ViralScoreCard";
import EmptyState from "@/components/EmptyState";
import { listClips } from "@/lib/api";
import { clipScore } from "@/lib/types";
import type { Clip } from "@/lib/types";

export default function ScoresPage() {
  const [clips, setClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listClips()
      .then((c) => setClips([...c].sort((a, b) => (clipScore(b) ?? -1) - (clipScore(a) ?? -1))))
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load scores."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Topbar title="Viral Score" />
      <main className="p-4 sm:p-6 space-y-4 min-w-0">
        <p className="text-slate-400 text-sm max-w-2xl">
          Clips ranked by viral score — but a score is never shown bare. Each card shows the 7-factor
          breakdown with reasons, why the moment was selected (when the API provides it), and the
          quality-gate result. Only 3–5 clips per video make it this far.
        </p>
        {loading && <p className="text-slate-400">Loading scores…</p>}
        {error && <p className="text-sm text-red-300">{error}</p>}
        {!loading && !error && clips.length === 0 && (
          <EmptyState title="No scored clips yet" message="Scores appear here once a video has been analysed and clips generated." actionHref="/upload" actionLabel="Upload a video" />
        )}
        <div className="space-y-4 max-w-3xl w-full min-w-0">
          {clips.map((c, i) => (
            <div key={String(c.id)}>
              <p className="text-sm text-slate-400 mb-2 break-words">#{i + 1} — {c.title}</p>
              <ViralScoreCard clip={c} />
            </div>
          ))}
        </div>
      </main>
    </>
  );
}
