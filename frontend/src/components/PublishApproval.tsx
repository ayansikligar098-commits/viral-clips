"use client";
import { useEffect, useState } from "react";
import { listInstagramAccounts, publishClip } from "@/lib/api";
import { clipDetectedLanguage, clipHashtags, clipSelectedCaption, clipSelectedHook } from "@/lib/types";
import type { Clip, InstagramAccount } from "@/lib/types";

// Approval-gated publishing: nothing is published without the explicit
// checkbox, and scheduling is a real publish_at sent to POST /api/publish.
// No manual caption writing is required: the exact caption + hashtags
// shown here come from the saved/edited clip (the API version), and that
// exact text is what is sent to the backend.
export default function PublishApproval({
  clipId,
  clip,
  caption,
  hashtags,
}: {
  clipId: string | number;
  clip?: Clip | null;
  caption?: string | null;
  hashtags?: string[];
}) {
  const [approved, setApproved] = useState(false);
  const [accounts, setAccounts] = useState<InstagramAccount[]>([]);
  const [accountId, setAccountId] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listInstagramAccounts().then(setAccounts).catch(() => setAccounts([]));
  }, []);

  // The exact text that will be published: the saved/edited caption from
  // the API (selected_caption first), plus the saved hashtags.
  const baseCaption = (clip ? clipSelectedCaption(clip) : null) ?? caption ?? "";
  const tagList = clip ? clipHashtags(clip) : (hashtags ?? []);
  const tagsText = tagList.map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" ");
  const publishCaption =
    baseCaption && tagsText && !baseCaption.includes("#")
      ? `${baseCaption}\n\n${tagsText}`
      : baseCaption || tagsText;
  const selectedHook = clip ? clipSelectedHook(clip) : null;
  const detectedLanguage = clip ? clipDetectedLanguage(clip) : null;

  async function submit(schedule: boolean) {
    if (!approved) { setError("Approval is required before publishing."); return; }
    setError(null); setStatus(null); setBusy(true);
    try {
      const publishAt = schedule && scheduledAt ? new Date(scheduledAt).toISOString() : null;
      const job = await publishClip(clipId, {
        instagram_account_id: accountId ? Number(accountId) : undefined,
        scheduled_at: publishAt,
        publish_at: publishAt,
        caption: publishCaption || undefined,
        approved: true,
      });
      setStatus(
        schedule
          ? `Scheduled for ${scheduledAt} (publish job #${String(job.id)}, status: ${job.status}).`
          : `Publish requested (job #${String(job.id)}, status: ${job.status}).` +
            (job.permalink ? ` Permalink: ${job.permalink}` : ""),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Publish failed.");
    } finally { setBusy(false); }
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 space-y-4 min-w-0">
      <h3 className="font-semibold text-white">Publish to Instagram</h3>
      <p className="text-sm text-slate-400">Publishing is approval-gated. Nothing is posted until you tick the box below. No caption writing needed — the saved version below is what gets published.</p>

      {/* Exact caption + hashtags that will be published (saved version). */}
      <div className="rounded-xl border border-white/10 bg-ink p-4 space-y-2">
        <p className="text-xs uppercase tracking-wide text-slate-400">Will be published — exact caption</p>
        {publishCaption ? (
          <p className="text-sm text-slate-100 whitespace-pre-line break-words">{publishCaption}</p>
        ) : (
          <p className="text-sm text-slate-500">No caption returned by the API yet — save the clip first, or the backend caption will be used.</p>
        )}
        {tagList.length > 0 && (
          <p className="text-xs text-slate-400">{tagList.length} hashtags included above.</p>
        )}
        {selectedHook && <p className="text-xs text-slate-400">Hook: {selectedHook}</p>}
        {detectedLanguage && <p className="text-xs text-slate-400">Language: {detectedLanguage}</p>}
        {clip?.title && <p className="text-xs text-slate-400">Clip: {clip.title}</p>}
      </div>

      <label className="flex items-start gap-2 text-sm text-slate-200">
        <input type="checkbox" checked={approved} onChange={(e) => setApproved(e.target.checked)} className="mt-0.5" />
        <span>I approve publishing this clip to Instagram with the caption above.</span>
      </label>
      <div>
        <label className="block text-sm text-slate-300 mb-1">Instagram account</label>
        <select value={accountId} onChange={(e) => setAccountId(e.target.value)} className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white">
          <option value="">Default connected account</option>
          {accounts.map((a) => <option key={String(a.id)} value={String(a.id)}>{a.username ?? `Account ${String(a.id)}`}</option>)}
        </select>
        {accounts.length === 0 && <p className="text-xs text-slate-500 mt-1">No accounts loaded — connect one on the Instagram page first.</p>}
      </div>
      <div>
        <label className="block text-sm text-slate-300 mb-1">Schedule for (publish_at, optional)</label>
        <input type="datetime-local" value={scheduledAt} onChange={(e) => setScheduledAt(e.target.value)} className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white" />
        {scheduledAt && <p className="text-xs text-slate-500 mt-1">Will publish at {new Date(scheduledAt).toLocaleString()}.</p>}
      </div>
      {error && <p className="text-sm text-red-300">{error}</p>}
      {status && <p className="text-sm text-emerald-300">{status}</p>}
      <div className="flex flex-col sm:flex-row gap-2">
        <button onClick={() => submit(false)} disabled={busy || !approved} title={!approved ? "Tick the approval checkbox first" : undefined}
          className="inline-flex min-h-[44px] items-center justify-center px-4 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed">
          {busy ? "Working…" : "Publish now"}
        </button>
        <button onClick={() => submit(true)} disabled={busy || !approved || !scheduledAt} title={!approved ? "Tick the approval checkbox first" : !scheduledAt ? "Pick a date and time to schedule" : undefined}
          className="inline-flex min-h-[44px] items-center justify-center px-4 py-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm disabled:opacity-50 disabled:cursor-not-allowed">
          Schedule
        </button>
      </div>
    </div>
  );
}
