"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Topbar from "@/components/Topbar";
import EmptyState from "@/components/EmptyState";
import { listPublishJobs } from "@/lib/api";
import type { PublishJob } from "@/lib/types";

export default function CalendarPage() {
  const [jobs, setJobs] = useState<PublishJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listPublishJobs()
      .then((j) => setJobs([...j].sort((a, b) => String(a.scheduled_at ?? a.created_at ?? "").localeCompare(String(b.scheduled_at ?? b.created_at ?? "")))))
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load publishing calendar."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Topbar title="Publishing Calendar" />
      <main className="p-4 sm:p-6 space-y-4 min-w-0">
        <p className="text-slate-400 text-sm">Scheduled and published clips, from real publish jobs in the API. Scheduling is done in our database — Meta has no native Reels scheduling.</p>
        {loading && <p className="text-slate-400">Loading calendar…</p>}
        {error && <p className="text-sm text-red-300">{error}</p>}
        {!loading && !error && jobs.length === 0 && (
          <EmptyState title="Nothing scheduled yet" message="Approve a clip in the Clip Editor and schedule it — it will appear here with its date and status." actionHref="/clips" actionLabel="Go to clips" />
        )}
        <div className="space-y-3">
          {jobs.map((j) => (
            <div key={String(j.id)} className="rounded-2xl border border-white/10 bg-panel p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="font-medium text-white break-words">{j.clip_title ?? `Clip ${String(j.clip_id ?? "")}`}</p>
                <p className="text-xs text-slate-400 mt-1 break-words">
                  {j.scheduled_at ? `Scheduled: ${new Date(j.scheduled_at).toLocaleString()}` : j.published_at ? `Published: ${new Date(j.published_at).toLocaleString()}` : "No date set"}
                  {j.error ? ` · Error: ${j.error}` : ""}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <span className="px-2.5 py-1 rounded-full text-xs bg-white/10 text-slate-200">{j.status}</span>
                {j.permalink && <a href={j.permalink} target="_blank" rel="noreferrer" className="text-sm text-violet-300 hover:text-violet-200">View post →</a>}
                {j.clip_id != null && <Link href={`/clips/${j.clip_id}`} className="text-sm text-violet-300 hover:text-violet-200">Open clip</Link>}
              </div>
            </div>
          ))}
        </div>
      </main>
    </>
  );
}
