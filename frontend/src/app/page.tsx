"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Topbar from "@/components/Topbar";
import ClipCard from "@/components/ClipCard";
import EmptyState from "@/components/EmptyState";
import { ApiError, clearToken, isLoggedIn, listClips, listPublishJobs, listVideos } from "@/lib/api";
import { clipScore } from "@/lib/types";
import type { Clip, PublishJob, Video } from "@/lib/types";

export default function Dashboard() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [clips, setClips] = useState<Clip[]>([]);
  const [published, setPublished] = useState<PublishJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Signed-out visitors have no token, so the protected dashboard calls
  // would fail with "Missing Authorization header". Don't call them at
  // all — show a sign-in prompt instead.
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) {
      setAuthed(false);
      setLoading(false);
      return;
    }
    setAuthed(true);
    Promise.all([listVideos(), listClips(), listPublishJobs()])
      .then(([v, c, p]) => {
        setVideos(v); setClips(c);
        setPublished(p.filter((j) => ["published", "complete", "completed"].includes((j.status || "").toLowerCase())));
      })
      .catch((err) => {
        // Expired/invalid token: drop it and show the sign-in prompt
        // instead of the raw backend error.
        if (err instanceof ApiError && err.status === 401) {
          clearToken();
          setAuthed(false);
          setError(null);
          return;
        }
        setError(err instanceof Error ? err.message : "Could not load dashboard data.");
      })
      .finally(() => setLoading(false));
  }, []);

  const passed = clips.filter((c) => c.quality_gate_passed === true);
  const recent = [...clips]
    .sort((a, b) => (clipScore(b) ?? -1) - (clipScore(a) ?? -1))
    .slice(0, 3);

  return (
    <>
      <Topbar title="Dashboard" />
      <main className="p-4 sm:p-6 space-y-6 min-w-0">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:justify-between">
          <p className="text-slate-400 text-sm">Quality over quantity — 3–5 strong clips per video, each quality-gated and scored with reasons.</p>
          <Link href="/upload" className="inline-flex min-h-[44px] items-center justify-center shrink-0 px-4 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium">Upload video</Link>
        </div>
        {loading && <p className="text-slate-400">Loading your projects…</p>}
        {!loading && !authed && !error && (
          <div className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-6 space-y-3">
            <h2 className="text-lg font-semibold text-white">Log in to see your videos and clips</h2>
            <p className="text-sm text-slate-400">Your projects live behind your account. Sign up free or log in, then upload a video or paste a YouTube link to get your first clips.</p>
            <div className="flex flex-wrap gap-2">
              <Link href="/register" className="inline-flex min-h-[44px] items-center px-4 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium">Sign up free</Link>
              <Link href="/login" className="inline-flex min-h-[44px] items-center px-4 py-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm font-medium">Log in</Link>
            </div>
          </div>
        )}
        {error && (
          <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-4">
            <p className="text-red-200 text-sm">{error}</p>
            <p className="text-red-200/70 text-xs mt-1">Check the backend is running at the API URL shown in Settings, then refresh.</p>
          </div>
        )}
        {!loading && !error && authed && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
              {[
                { label: "Videos", value: videos.length },
                { label: "Clips generated", value: clips.length },
                { label: "Quality-gate passed", value: passed.length },
                { label: "Published", value: published.length },
              ].map((s) => (
                <div key={s.label} className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 min-w-0">
                  <p className="text-2xl sm:text-3xl font-bold text-white">{s.value}</p>
                  <p className="text-sm text-slate-400 mt-1">{s.label}</p>
                </div>
              ))}
            </div>
            {clips.length === 0 ? (
              <EmptyState
                title="No clips yet"
                message="Upload a long video and the pipeline will analyse it and return 3–5 strong clips — not 10–20 random ones. Each clip is scored and quality-gated before you see it."
                actionHref="/upload" actionLabel="Upload your first video"
              />
            ) : (
              <section>
                <h2 className="text-lg font-semibold text-white mb-3">Top clips</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {recent.map((c) => <ClipCard key={String(c.id)} clip={c} />)}
                </div>
                <Link href="/clips" className="inline-block mt-4 text-sm text-violet-300 hover:text-violet-200">View all clips →</Link>
              </section>
            )}
          </>
        )}
      </main>
    </>
  );
}
