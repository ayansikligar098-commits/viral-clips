"use client";
import { useEffect, useState } from "react";
import { getJob } from "@/lib/api";
import type { Job } from "@/lib/types";

// Polls GET /api/jobs/{id} every 2s until the job finishes or fails.
export default function JobProgress({ jobId }: { jobId: string | number }) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | undefined;
    async function poll() {
      try {
        const j = await getJob(jobId);
        if (cancelled) return;
        setJob(j);
        const done = ["completed", "complete", "done", "failed", "error", "cancelled"].includes((j.status || "").toLowerCase());
        if (done && timer) clearInterval(timer);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load job status.");
        if (timer) clearInterval(timer);
      }
    }
    poll();
    timer = setInterval(poll, 2000);
    return () => { cancelled = true; if (timer) clearInterval(timer); };
  }, [jobId]);

  if (error) return <p className="text-sm text-red-300">{error}</p>;
  if (!job) return <p className="text-sm text-slate-400">Loading job status…</p>;
  const pct = job.progress ?? 0;
  const failed = ["failed", "error"].includes((job.status || "").toLowerCase());
  return (
    <div className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 min-w-0">
      <div className="flex flex-wrap justify-between gap-2 text-sm">
        <span className="text-white font-medium break-words min-w-0">{job.stage || job.status}</span>
        <span className="text-slate-400 shrink-0">{pct}% · {job.status}</span>
      </div>
      <div className="h-2 bg-white/10 rounded-full mt-2 overflow-hidden">
        <div className={`h-full rounded-full ${failed ? "bg-red-500" : "bg-violet-500"}`} style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
      </div>
      {job.message && <p className="text-sm text-slate-400 mt-2">{job.message}</p>}
      {job.error && <p className="text-sm text-red-300 mt-2">{job.error}</p>}
      <p className="text-xs text-slate-500 mt-2">Job #{String(job.id)} · polled every 2s from the API.</p>
    </div>
  );
}
