"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Topbar from "@/components/Topbar";
import JobProgress from "@/components/JobProgress";
import ClipCard from "@/components/ClipCard";
import { getAnalysis, getVideo, listClips, listJobs, startAnalysis } from "@/lib/api";
import type { AnalysisResult, Clip, Job, Video } from "@/lib/types";

export default function AnalysisDetailPage({ params }: { params: { videoId: string } }) {
  const [video, setVideo] = useState<Video | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    Promise.all([
      getVideo(params.videoId),
      listJobs().then((js) => js.find((j) => String(j.video_id) === params.videoId) ?? null),
      getAnalysis(params.videoId).catch(() => null),
      listClips(params.videoId).catch(() => [] as Clip[]),
    ])
      .then(([v, j, a, c]) => { setVideo(v); setJob(j); setAnalysis(a); setClips(c); })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load this video."))
      .finally(() => setLoading(false));
  }, [params.videoId]);

  async function start() {
    setStarting(true); setError(null);
    try { setJob(await startAnalysis(params.videoId)); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not start analysis."); }
    finally { setStarting(false); }
  }

  const transcript = analysis?.transcript_text ?? analysis?.transcript ?? null;

  return (
    <>
      <Topbar title="Video Analysis" />
      <main className="p-4 sm:p-6 space-y-5 min-w-0">
        {loading && <p className="text-slate-400">Loading analysis…</p>}
        {error && <p className="text-sm text-red-300">{error}</p>}
        {video && (
          <div>
            <h2 className="text-lg font-semibold text-white break-words">{video.title || video.original_filename || video.filename || `Video ${params.videoId}`}</h2>
            <p className="text-sm text-slate-400">{video.duration != null ? `${Math.round(video.duration)}s · ` : ""}{video.status ?? ""}</p>
          </div>
        )}
        {!loading && !job && (
          <div className="rounded-2xl border border-white/10 bg-panel p-5">
            <p className="text-slate-300 text-sm">No analysis job for this video yet.</p>
            <button onClick={start} disabled={starting} className="mt-3 inline-flex min-h-[44px] items-center px-4 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium disabled:opacity-50">
              {starting ? "Starting…" : "Start analysis"}
            </button>
          </div>
        )}
        {job && <JobProgress jobId={job.id} />}
        {job && (
          <button onClick={start} disabled={starting} className="inline-flex min-h-[44px] items-center px-4 py-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm disabled:opacity-50">
            {starting ? "Starting…" : "Re-run analysis"}
          </button>
        )}
        {analysis?.summary && (
          <section className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 min-w-0">
            <h3 className="font-semibold text-white mb-2">Summary</h3>
            <p className="text-sm text-slate-300 whitespace-pre-wrap break-words">{analysis.summary}</p>
          </section>
        )}
        {analysis?.scenes && analysis.scenes.length > 0 && (
          <section className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 min-w-0">
            <h3 className="font-semibold text-white mb-2">Scenes</h3>
            <ul className="text-sm text-slate-300 space-y-1">
              {analysis.scenes.map((s, i) => (
                <li key={i}>{s.start != null ? `${Math.round(s.start)}s` : ""}{s.end != null ? ` – ${Math.round(s.end)}s` : ""}{s.description ? ` — ${s.description}` : ""}</li>
              ))}
            </ul>
          </section>
        )}
        {transcript && (
          <section className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 min-w-0">
            <h3 className="font-semibold text-white mb-2">Transcript</h3>
            <p className="text-sm text-slate-300 whitespace-pre-wrap break-words max-h-96 overflow-y-auto">{transcript}</p>
          </section>
        )}
        {!loading && !transcript && !analysis?.summary && (
          <p className="text-sm text-slate-500">No transcript or summary returned by the API yet — it appears once analysis finishes.</p>
        )}
        {clips.length > 0 && (
          <section>
            <h3 className="font-semibold text-white mb-3">Clips from this video ({clips.length} — quality-gated, best first)</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{clips.map((c) => <ClipCard key={String(c.id)} clip={c} />)}</div>
          </section>
        )}
        <Link href="/clips" className="inline-block text-sm text-violet-300 hover:text-violet-200">View all clips →</Link>
      </main>
    </>
  );
}
