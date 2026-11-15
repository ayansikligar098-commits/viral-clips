"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Topbar from "@/components/Topbar";
import EmptyState from "@/components/EmptyState";
import { listJobs, listVideos } from "@/lib/api";
import type { Job, Video } from "@/lib/types";

export default function AnalysisListPage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listVideos(), listJobs()])
      .then(([v, j]) => { setVideos(v); setJobs(j); })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load analysis data."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Topbar title="Video Analysis" />
      <main className="p-4 sm:p-6 space-y-4 min-w-0">
        {loading && <p className="text-slate-400">Loading…</p>}
        {error && <p className="text-sm text-red-300">{error}</p>}
        {!loading && !error && videos.length === 0 && (
          <EmptyState title="No videos yet" message="Upload a video to start analysis — transcription, scene detection and moment scoring." actionHref="/upload" actionLabel="Upload a video" />
        )}
        {!loading && !error && videos.length > 0 && (
          <div className="space-y-3">
            {videos.map((v) => {
              const job = jobs.find((j) => String(j.video_id) === String(v.id));
              return (
                <div key={String(v.id)} className="rounded-2xl border border-white/10 bg-panel p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-white break-words">{v.title || v.original_filename || v.filename || `Video ${String(v.id)}`}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {v.duration != null ? `${Math.round(v.duration)}s · ` : ""}{v.status ?? ""}
                      {job ? ` · Job: ${job.status} (${job.progress ?? 0}%)` : ""}
                    </p>
                  </div>
                  <Link href={`/analysis/${v.id}`} className="inline-flex min-h-[44px] items-center justify-center shrink-0 px-3 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm">View analysis</Link>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </>
  );
}
