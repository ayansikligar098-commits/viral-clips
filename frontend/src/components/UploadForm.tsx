"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { createVideoFromUrl, isLoggedIn, uploadVideo } from "@/lib/api";

// Backend limit is 2 GB; the free test deployment handles files under
// 500 MB far more reliably. No chunked/resumable upload in this task —
// just a clear warning + size display before the user starts uploading.
const BACKEND_LIMIT_MB = 2000;
const RECOMMENDED_MAX_MB = 500;
// Free-test guard for YouTube downloads (enforced server-side too).
const YOUTUBE_MAX_MINUTES = 15;

export default function UploadForm() {
  const router = useRouter();
  const [mode, setMode] = useState<"file" | "youtube">("file");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [attested, setAttested] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // YouTube-link tab state.
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [downloading, setDownloading] = useState(false);

  const fileSizeMB = file ? file.size / 1_000_000 : 0;
  const tooLarge = fileSizeMB > BACKEND_LIMIT_MB;
  const largeForFreeTest = fileSizeMB > RECOMMENDED_MAX_MB && !tooLarge;

  async function submitFile(e: React.FormEvent) {
    e.preventDefault();
    if (!isLoggedIn()) { setError("Please log in or sign up first — uploads need an account."); return; }
    if (!file) { setError("Choose a video file first."); return; }
    if (tooLarge) { setError(`This file is ${fileSizeMB.toFixed(0)} MB — over the backend limit of ${BACKEND_LIMIT_MB / 1000} GB. Choose a smaller file.`); return; }
    if (!attested) { setError("Ownership attestation is required before uploading."); return; }
    setError(null); setBusy(true); setProgress(0);
    try {
      const video = await uploadVideo(file, { title: title || undefined, ownsContent: attested, onProgress: setProgress });
      router.push(`/analysis/${video.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitYoutube(e: React.FormEvent) {
    e.preventDefault();
    if (!isLoggedIn()) { setError("Please log in or sign up first — fetching a YouTube video needs an account."); return; }
    const url = youtubeUrl.trim();
    if (!url) { setError("Paste a YouTube video link first."); return; }
    if (!attested) { setError("Ownership attestation is required before fetching a YouTube video."); return; }
    setError(null); setBusy(true); setDownloading(true);
    try {
      const { video } = await createVideoFromUrl(url, { title: title || undefined, ownsContent: attested });
      // Same destination as file upload: the analysis page polls JobProgress
      // for the job the backend created for the downloaded video.
      router.push(`/analysis/${video.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not fetch that YouTube video.");
    } finally {
      setBusy(false); setDownloading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-6 space-y-4 max-w-2xl w-full">
      <div role="tablist" aria-label="Upload method" className="grid grid-cols-2 gap-2">
        <button
          type="button" role="tab" aria-selected={mode === "file"}
          onClick={() => { setMode("file"); setError(null); }}
          className={`min-h-[44px] rounded-lg px-3 py-2.5 text-sm font-medium ${mode === "file" ? "bg-violet-600 text-white" : "bg-white/5 text-slate-300 hover:bg-white/10"}`}
        >
          File Upload
        </button>
        <button
          type="button" role="tab" aria-selected={mode === "youtube"}
          onClick={() => { setMode("youtube"); setError(null); }}
          className={`min-h-[44px] rounded-lg px-3 py-2.5 text-sm font-medium ${mode === "youtube" ? "bg-violet-600 text-white" : "bg-white/5 text-slate-300 hover:bg-white/10"}`}
        >
          YouTube Link
        </button>
      </div>

      {mode === "file" ? (
        <form onSubmit={submitFile} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-200 mb-1">Video file</label>
            <input
              type="file"
              accept="video/*"
              disabled={busy}
              onChange={(e) => { setFile(e.target.files?.[0] ?? null); setProgress(null); setError(null); }}
              className="block w-full min-h-[44px] text-sm text-slate-300 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-violet-600 file:text-white"
            />
            {file && (
              <p className="text-xs text-slate-400 mt-2 break-words">
                {file.name} · {fileSizeMB.toFixed(1)} MB
              </p>
            )}
            {largeForFreeTest && (
              <div className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
                <p className="text-xs text-amber-200">
                  Large file ({fileSizeMB.toFixed(0)} MB): the backend limit is 2 GB, but for the free test
                  deployment files under 500 MB upload and process much more reliably. A smaller export
                  (or trimming the video first) is recommended.
                </p>
              </div>
            )}
            {tooLarge && (
              <div className="mt-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3">
                <p className="text-xs text-red-200">
                  This file is over the 2 GB backend limit and cannot be uploaded. Choose a smaller file.
                </p>
              </div>
            )}
            {!file && (
              <p className="text-xs text-slate-500 mt-2">
                Backend limit: 2 GB. For the free test, files under 500 MB are recommended.
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-200 mb-1">Title (optional)</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Podcast Ep. 12 — AI and creativity"
              className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white" />
          </div>
          <label className="flex items-start gap-2 text-sm text-slate-300">
            <input type="checkbox" checked={attested} onChange={(e) => setAttested(e.target.checked)} className="mt-1 min-h-[20px] min-w-[20px]" />
            <span>I confirm I own this video or have a licence to use it, and I will not upload content I do not have rights to.</span>
          </label>
          {progress != null && (
            <div>
              <div className="h-2 bg-white/10 rounded-full overflow-hidden"><div className="h-full bg-violet-500" style={{ width: `${progress}%` }} /></div>
              <p className="text-xs text-slate-400 mt-1">Uploading… {progress}%</p>
            </div>
          )}
          {error && <p className="text-sm text-red-300 break-words">{error}</p>}
          <button type="submit" disabled={busy || !file || !attested || tooLarge}
            className="w-full sm:w-auto inline-flex min-h-[44px] items-center justify-center px-4 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            title={!attested ? "Tick the ownership attestation to enable upload" : tooLarge ? "File is over the 2 GB limit" : undefined}>
            {busy ? `Uploading… ${progress ?? 0}%` : "Upload video"}
          </button>
          {!attested && <p className="text-xs text-slate-500">Upload is disabled until you confirm ownership above.</p>}
        </form>
      ) : (
        <form onSubmit={submitYoutube} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-200 mb-1">YouTube video link</label>
            <input
              type="url" inputMode="url" autoCapitalize="off" autoCorrect="off" spellCheck={false}
              value={youtubeUrl} disabled={busy}
              onChange={(e) => { setYoutubeUrl(e.target.value); setError(null); }}
              placeholder="https://www.youtube.com/watch?v=…"
              className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white placeholder:text-slate-500"
            />
            <p className="text-xs text-slate-500 mt-2">
              Paste a link to a video you own (watch, youtu.be, or Shorts). The backend downloads it
              (720p max) and runs the same AI analysis and clip pipeline as a file upload.
              Free test: videos up to {YOUTUBE_MAX_MINUTES} minutes only.
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-200 mb-1">Title (optional)</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Leave blank to use the YouTube title"
              className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white" />
          </div>
          <label className="flex items-start gap-2 text-sm text-slate-300">
            <input type="checkbox" checked={attested} onChange={(e) => setAttested(e.target.checked)} className="mt-1 min-h-[20px] min-w-[20px]" />
            <span>I confirm I own this YouTube video or have a licence to use it, and I will not fetch content I do not have rights to.</span>
          </label>
          {downloading && (
            <div>
              <div className="h-2 bg-white/10 rounded-full overflow-hidden"><div className="h-full bg-violet-500 animate-pulse w-full" /></div>
              <p className="text-xs text-slate-400 mt-1">Downloading from YouTube… this can take a minute. Job progress will show on the analysis page next.</p>
            </div>
          )}
          {error && <p className="text-sm text-red-300 break-words">{error}</p>}
          <button type="submit" disabled={busy || !youtubeUrl.trim() || !attested}
            className="w-full sm:w-auto inline-flex min-h-[44px] items-center justify-center px-4 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            title={!attested ? "Tick the ownership attestation to enable fetching" : undefined}>
            {busy ? "Fetching video…" : "Fetch video & create clips"}
          </button>
          {!attested && <p className="text-xs text-slate-500">Fetching is disabled until you confirm ownership above.</p>}
        </form>
      )}
    </div>
  );
}
