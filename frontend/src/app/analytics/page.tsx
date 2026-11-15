"use client";
import { useEffect, useState } from "react";
import Topbar from "@/components/Topbar";
import EmptyState from "@/components/EmptyState";
import { getAnalytics } from "@/lib/api";
import type { AnalyticsSummary } from "@/lib/types";

// Real data only: this page shows what /api/analytics returns, or a clear
// "No data yet" empty state. No mock analytics anywhere.
export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAnalytics()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load analytics."))
      .finally(() => setLoading(false));
  }, []);

  const hasData =
    data != null &&
    ((data.total_views ?? 0) > 0 || (data.total_likes ?? 0) > 0 || (data.per_clip?.length ?? 0) > 0 || (data.clips_published ?? 0) > 0);
  const maxViews = Math.max(1, ...(data?.per_clip ?? []).map((c) => c.views ?? 0));

  return (
    <>
      <Topbar title="Analytics" />
      <main className="p-4 sm:p-6 space-y-4 min-w-0">
        <p className="text-slate-400 text-sm">Insights from the Instagram Graph API, ingested by the backend. Until clips are published and insights return, this page honestly says so.</p>
        {loading && <p className="text-slate-400">Loading analytics…</p>}
        {error && <p className="text-sm text-red-300">{error}</p>}
        {!loading && !error && !hasData && (
          <EmptyState title="No data yet" message="No analytics data has been returned by the API yet. Publish a clip, wait for Instagram insights to be ingested, and real numbers will appear here." actionHref="/clips" actionLabel="Go to clips" />
        )}
        {!loading && !error && hasData && data && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
              {[
                { label: "Total views", value: data.total_views ?? 0 },
                { label: "Total reach", value: data.total_reach ?? 0 },
                { label: "Likes", value: data.total_likes ?? 0 },
                { label: "Comments", value: data.total_comments ?? 0 },
                { label: "Shares", value: data.total_shares ?? 0 },
                { label: "Saves", value: data.total_saves ?? 0 },
              ].map((s) => (
                <div key={s.label} className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 min-w-0">
                  <p className="text-2xl sm:text-3xl font-bold text-white break-words">{s.value.toLocaleString()}</p>
                  <p className="text-sm text-slate-400 mt-1">{s.label}</p>
                </div>
              ))}
            </div>
            {data.per_clip && data.per_clip.length > 0 && (
              <section className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 min-w-0">
                <h3 className="font-semibold text-white mb-4">Views per clip</h3>
                <div className="space-y-3">
                  {data.per_clip.map((c) => (
                    <div key={String(c.clip_id)}>
                      <div className="flex flex-wrap justify-between gap-2 text-sm"><span className="text-slate-200 break-words min-w-0">{c.title ?? `Clip ${String(c.clip_id)}`}</span><span className="text-slate-400 shrink-0 whitespace-nowrap">{(c.views ?? 0).toLocaleString()} views</span></div>
                      <div className="h-2 bg-white/10 rounded-full mt-1 overflow-hidden"><div className="h-full bg-violet-500" style={{ width: `${Math.round(((c.views ?? 0) / maxViews) * 100)}%` }} /></div>
                      <p className="text-xs text-slate-500 mt-1">{c.likes ?? 0} likes · {c.comments ?? 0} comments · {c.shares ?? 0} shares · {c.saves ?? 0} saves</p>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </>
  );
}
