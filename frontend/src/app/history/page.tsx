"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Topbar from "@/components/Topbar";
import EmptyState from "@/components/EmptyState";
import { listJobs, listVideos } from "@/lib/api";
import type { Job, Video } from "@/lib/types";

export default function HistoryPage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listVideos(), listJobs()])
      .then(([v, j]) => { setVideos(v); setJobs(j); })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load history."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Topbar title="Project History" />
      <main className="p-4 sm:p-6 space-y-5 min-w-0">
        {loading && <p className="text-slate-400">Loading history…</p>}
        {error && <p className="text-sm text-red-300">{error}</p>}
        {!loading && !error && videos.length === 0 && jobs.length === 0 && (
          <EmptyState title="No history yet" message="Videos you upload and analysis jobs you run will be listed here." actionHref="/upload" actionLabel="Upload a video" />
        )}
        {videos.length > 0 && (
          <section>
            <h2 className="font-semibold text-white mb-3">Videos</h2>
            <div className="space-y-2">
              {videos.map((v) => (
                <div key={String(v.id)} className="rounded-xl border border-white/10 bg-panel px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <span className="text-slate-200 break-words min-w-0">{v.title || v.original_filename || v.filename || `Video ${String(v.id)}`}</span>
                  <Link href={`/analysis/${v.id}`} className="text-sm text-violet-300">View →</Link>
                </div>
              ))}
            </div>
          </section>
        )}
        {jobs.length > 0 && (
          <section>
            <h2 className="font-semibold text-white mb-3">Jobs</h2>
            <div className="space-y-2">
              {jobs.map((j) => (
                <div key={String(j.id)} className="rounded-xl border border-white/10 bg-panel px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-sm">
                  <span className="text-slate-200 break-words min-w-0">Job #{String(j.id)}{j.video_id != null ? ` · Video ${String(j.video_id)}` : ""}</span>
                  <span className="text-slate-400">{j.stage || j.status} · {j.progress ?? 0}%</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </>
  );
}
