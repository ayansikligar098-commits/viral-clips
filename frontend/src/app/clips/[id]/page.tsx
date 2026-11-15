"use client";
import { useEffect, useState } from "react";
import Topbar from "@/components/Topbar";
import ViralScoreCard from "@/components/ViralScoreCard";
import PublishApproval from "@/components/PublishApproval";
import { clipCoverUrlOrNull, clipFileUrl, getClip, renderClip, updateClip } from "@/lib/api";
import {
  CAPTION_PRESETS,
  EDITING_STYLES,
  clipCaptionVariations,
  clipContextReason,
  clipDetectedLanguage,
  clipEnd,
  clipHashtags,
  clipHookVariations,
  clipSelectedCaption,
  clipSelectedHook,
  clipStart,
  clipTitleVariations,
  clipWords,
  resolveCaptionPreset,
} from "@/lib/types";
import type { Clip } from "@/lib/types";

// CTA quick picks — user-chosen only; the field is pre-filled from the API
// (clip.cta) when the backend returns one, otherwise left empty.
const CTA_OPTIONS = ["Follow for more", "Comment below", "Share this", "Save this"] as const;

export default function ClipEditorPage({ params }: { params: { id: string } }) {
  const [clip, setClip] = useState<Clip | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [caption, setCaption] = useState("");
  const [selectedCaption, setSelectedCaption] = useState("");
  const [selectedHook, setSelectedHook] = useState("");
  const [cta, setCta] = useState("");
  const [hashtags, setHashtags] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  // Subtitle preset — DISTINCT from the editing style below. Sent verbatim
  // as `caption_style` in POST /api/clips/{id}/render.
  const [captionStyle, setCaptionStyle] = useState("Bold Yellow");
  // Phase 1 — editing style: a real API parameter, sent as `style` in
  // POST /api/clips/{id}/render. Framing/captions are backend-driven;
  // no tracking assumptions are hardcoded in this UI.
  const [style, setStyle] = useState("podcast");
  const [saving, setSaving] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    getClip(params.id)
      .then((c) => {
        setClip(c);
        setTitle(c.title || "");
        // Auto-generated caption, pre-selected: the backend's saved
        // selection first, else the first caption variation, else caption.
        const autoCaption =
          clipSelectedCaption(c) ?? clipCaptionVariations(c)[0] ?? "";
        setCaption(autoCaption);
        setSelectedCaption(autoCaption);
        setSelectedHook(clipSelectedHook(c) ?? "");
        setCta(c.cta ?? "");
        setHashtags(clipHashtags(c).join(" "));
        setStart(clipStart(c) != null ? String(clipStart(c)) : "");
        setEnd(clipEnd(c) != null ? String(clipEnd(c)) : "");
        setCaptionStyle(resolveCaptionPreset(c.caption_style) ?? "Bold Yellow");
        setStyle(c.style ?? c.editing_style ?? "podcast");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load this clip."))
      .finally(() => setLoading(false));
  }, [params.id]);

  const selectedStyle = EDITING_STYLES.find((s) => s.value === style) ?? EDITING_STYLES[0];
  const selectedPreset = CAPTION_PRESETS.find((p) => p.value === captionStyle) ?? CAPTION_PRESETS[0];
  const titleVariations = clip ? clipTitleVariations(clip) : [];
  const captionVariations = clip ? clipCaptionVariations(clip) : [];
  const hookVariations = clip ? clipHookVariations(clip) : [];
  const detectedLanguage = clip ? clipDetectedLanguage(clip) : null;
  const coverUrl = clip ? clipCoverUrlOrNull(clip) : null;
  const words = clip ? clipWords(clip) : [];
  const hashtagList = hashtags.split(/[,\s]+/).filter(Boolean);

  function pickCaption(v: string) {
    setCaption(v);
    setSelectedCaption(v);
  }

  async function save() {
    if (!clip) return;
    setSaving(true); setError(null); setNotice(null);
    try {
      // PATCH /api/clips/{id} — the saved/edited version is what the
      // Publish flow uses. selected_* / cta are sent only when set.
      const patch: Parameters<typeof updateClip>[1] = {
        title,
        caption,
        hashtags: hashtagList,
        caption_style: captionStyle,
        style,
      };
      if (selectedCaption) patch.selected_caption = selectedCaption;
      if (selectedHook) patch.selected_hook = selectedHook;
      if (cta) patch.cta = cta;
      const updated = await updateClip(clip.id, patch);
      setClip(updated);
      // Re-sync local fields from the saved version the API returned.
      setTitle(updated.title || title);
      const savedCaption = clipSelectedCaption(updated) ?? caption;
      setCaption(savedCaption);
      setSelectedCaption(savedCaption);
      setSelectedHook(clipSelectedHook(updated) ?? selectedHook);
      setCta(updated.cta ?? cta);
      setHashtags(clipHashtags(updated).join(" "));
      setNotice("Saved. The Publish section below now uses this saved version.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally { setSaving(false); }
  }

  async function reRender() {
    if (!clip) return;
    setRendering(true); setError(null); setNotice(null);
    try {
      // `style` is sent verbatim — this is what chooses the editing preset
      // on the backend (Podcast / Gaming / Cinematic / Hormozi-inspired /
      // Minimal Captions). Trim + subtitle preset travel in the same request
      // (`caption_style` is the subtitle preset, distinct from `style`).
      const result = await renderClip(clip.id, {
        start_time: start ? Number(start) : undefined,
        end_time: end ? Number(end) : undefined,
        caption_style: captionStyle,
        style,
      });
      if (result && typeof result === "object" && "id" in result && "title" in result) {
        setClip(result as Clip);
      }
      setNotice(`Re-render requested with style “${selectedStyle.label}” and subtitle preset “${selectedPreset.label}”. Refresh to see the new render once the job finishes.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Re-render failed.");
    } finally { setRendering(false); }
  }

  return (
    <>
      <Topbar title="Clip Editor" />
      <main className="p-4 sm:p-6 space-y-5 max-w-5xl w-full min-w-0">
        {loading && <p className="text-slate-400">Loading clip…</p>}
        {error && <p className="text-sm text-red-300">{error}</p>}
        {clip && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div>
                <video src={clipFileUrl(clip)} controls playsInline preload="metadata" className="w-full h-auto aspect-[9/16] max-h-[560px] object-cover bg-black rounded-2xl" />
                <a href={clipFileUrl(clip)} download className="mt-3 inline-flex min-h-[44px] items-center px-4 py-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm font-medium">Download clip (.mp4)</a>
                <p className="text-xs text-slate-500 mt-2">
                  Trim {start || "—"}s – {end || "—"}s
                  {clip.style || clip.editing_style ? ` · Current style: ${clip.style ?? clip.editing_style}` : ""}
                  {clip.caption_style ? ` · Subtitle preset applied: ${clip.caption_style}` : ""}
                </p>
                {/* Cover thumbnail (1080x1920) from the API — shown only when returned. */}
                {coverUrl ? (
                  <div className="mt-4">
                    <p className="text-sm text-slate-300 mb-1">Cover thumbnail (1080×1920)</p>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={coverUrl} alt="Reel cover thumbnail" className="w-32 aspect-[9/16] object-cover bg-black rounded-xl border border-white/10" />
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 mt-4">No cover thumbnail returned by the API yet.</p>
                )}
                {detectedLanguage && (
                  <p className="mt-3">
                    <span className="px-2 py-0.5 rounded-full bg-white/10 text-slate-200 text-xs">Language: {detectedLanguage}</span>
                  </p>
                )}
              </div>
              <div className="space-y-4">
                <ViralScoreCard clip={clip} />
                {clipContextReason(clip) && (
                  <p className="text-xs text-slate-500">
                    Context shown above comes from the API only; it is omitted when the backend does not provide it.
                  </p>
                )}
              </div>
            </div>

            {/* Word-by-word subtitle preview info — API timings only. */}
            <section className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 space-y-2">
              <h3 className="font-semibold text-white">Subtitles (word-by-word)</h3>
              <p className="text-sm text-slate-400">
                Subtitles are burned into the render with the selected preset below
                {clip.caption_style ? <> — currently applied: <span className="text-slate-200">{clip.caption_style}</span></> : "."}
              </p>
              {words.length > 0 ? (
                <>
                  <p className="text-xs text-slate-400">
                    {words.length} words with timings
                    {detectedLanguage ? ` · Language: ${detectedLanguage}` : ""}:
                  </p>
                  <p className="text-sm text-slate-200 leading-relaxed">
                    {words.slice(0, 40).map((w, i) => (
                      <span key={i} title={w.start != null ? `${w.start.toFixed(1)}s – ${w.end != null ? w.end.toFixed(1) : "?"}s` : undefined} className="inline-block px-1 py-0.5 mr-1 mb-1 rounded bg-white/10">
                        {w.word}
                      </span>
                    ))}
                    {words.length > 40 && <span className="text-slate-400">… +{words.length - 40} more</span>}
                  </p>
                </>
              ) : clip.subtitle_preview ? (
                <p className="text-sm text-slate-200">{clip.subtitle_preview}</p>
              ) : (
                <p className="text-xs text-slate-500">
                  The API has not returned word timings for this clip yet, so no preview words are shown here — nothing is fabricated.
                </p>
              )}
            </section>

            <section className="rounded-2xl border border-white/10 bg-panel p-4 sm:p-5 space-y-4">
              <h3 className="font-semibold text-white">Edit clip</h3>
              <p className="text-sm text-slate-400">
                Everything below is auto-generated and pre-filled — editing is optional. Pick a variation or edit the fields, then Save.
              </p>
              <div>
                <label className="block text-sm text-slate-300 mb-1">Title (max 60 chars)</label>
                <input value={title} maxLength={60} onChange={(e) => setTitle(e.target.value)} className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white" />
              </div>

              {/* Auto-generated title variations — API only. */}
              {titleVariations.length > 0 && (
                <div>
                  <label className="block text-sm text-slate-300 mb-1">Title variations (auto-generated — pick one)</label>
                  <div className="space-y-2">
                    {titleVariations.map((v, i) => (
                      <button key={i} type="button" onClick={() => setTitle(v)} aria-pressed={title === v}
                        className={`block w-full min-h-[44px] text-left px-3 py-2 rounded-lg border text-sm ${title === v ? "border-violet-400 bg-violet-600/20 text-white" : "border-white/10 bg-ink text-slate-300 hover:border-white/25"}`}>
                        {v} {title === v && <span className="text-violet-300">· selected</span>}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm text-slate-300 mb-1">Instagram caption</label>
                <textarea value={caption} rows={3} onChange={(e) => pickCaption(e.target.value)} className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white" />
              </div>

              {/* Auto-generated caption variations — API only, default pre-selected. */}
              {captionVariations.length > 0 && (
                <div>
                  <label className="block text-sm text-slate-300 mb-1">Caption variations (auto-generated — pick one)</label>
                  <div className="space-y-2">
                    {captionVariations.map((v, i) => (
                      <button key={i} type="button" onClick={() => pickCaption(v)} aria-pressed={selectedCaption === v}
                        className={`block w-full min-h-[44px] text-left px-3 py-2 rounded-lg border text-sm whitespace-pre-line ${selectedCaption === v ? "border-violet-400 bg-violet-600/20 text-white" : "border-white/10 bg-ink text-slate-300 hover:border-white/25"}`}>
                        {v} {selectedCaption === v && <span className="text-violet-300">· selected</span>}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Auto-generated hook variations — API only. */}
              {hookVariations.length > 0 && (
                <div>
                  <label className="block text-sm text-slate-300 mb-1">Hook variations (auto-generated — pick one)</label>
                  <div className="space-y-2">
                    {hookVariations.map((v, i) => (
                      <button key={i} type="button" onClick={() => setSelectedHook(v)} aria-pressed={selectedHook === v}
                        className={`block w-full min-h-[44px] text-left px-3 py-2 rounded-lg border text-sm ${selectedHook === v ? "border-violet-400 bg-violet-600/20 text-white" : "border-white/10 bg-ink text-slate-300 hover:border-white/25"}`}>
                        {v} {selectedHook === v && <span className="text-violet-300">· selected</span>}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {hookVariations.length === 0 && selectedHook && (
                <p className="text-sm text-slate-300">Hook: {selectedHook}</p>
              )}

              <div>
                <label className="block text-sm text-slate-300 mb-1">Hashtags (space-separated{hashtagList.length > 0 ? ` · ${hashtagList.length} tags` : ""})</label>
                <input value={hashtags} onChange={(e) => setHashtags(e.target.value)} className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white" />
                {hashtagList.length > 0 && (
                  <p className="text-xs text-slate-400 mt-1">{hashtagList.map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" ")}</p>
                )}
              </div>

              <div>
                <label className="block text-sm text-slate-300 mb-1">Call to action (CTA)</label>
                <input value={cta} onChange={(e) => setCta(e.target.value)} placeholder="e.g. Follow for more" className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white" />
                <div className="flex flex-wrap gap-2 mt-2">
                  {CTA_OPTIONS.map((opt) => (
                    <button key={opt} type="button" onClick={() => setCta(opt)}
                      className={`inline-flex min-h-[44px] items-center px-3 py-2 rounded-lg text-sm ${cta === opt ? "bg-violet-600 text-white" : "bg-white/10 text-slate-300 hover:bg-white/20"}`}>
                      {opt}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                <div>
                  <label className="block text-sm text-slate-300 mb-1">Trim start (seconds)</label>
                  <input type="number" min={0} step={0.1} value={start} onChange={(e) => setStart(e.target.value)} className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white" />
                </div>
                <div>
                  <label className="block text-sm text-slate-300 mb-1">Trim end (seconds)</label>
                  <input type="number" min={0} step={0.1} value={end} onChange={(e) => setEnd(e.target.value)} className="w-full min-h-[44px] px-3 py-2.5 rounded-lg bg-ink border border-white/10 text-white" />
                </div>
              </div>

              {/* Subtitle preset selector — distinct from the editing style below. */}
              <div>
                <label className="block text-sm text-slate-300 mb-1">Subtitle preset</label>
                <div className="grid sm:grid-cols-2 gap-2">
                  {CAPTION_PRESETS.map((p) => (
                    <button key={p.value} type="button" onClick={() => setCaptionStyle(p.value)} aria-pressed={captionStyle === p.value}
                      className={`min-h-[44px] text-left px-3 py-2.5 rounded-xl border text-sm ${
                        captionStyle === p.value
                          ? "border-violet-400 bg-violet-600/20 text-white"
                          : "border-white/10 bg-ink text-slate-300 hover:border-white/25"
                      }`}>
                      <span className="block font-medium">{p.label}</span>
                      <span className="block text-xs text-slate-400 mt-0.5">{p.description}</span>
                    </button>
                  ))}
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  Selected: <span className="text-slate-300">{selectedPreset.label}</span>
                  {clip.caption_style ? <> · Currently applied by the backend: <span className="text-slate-300">{clip.caption_style}</span></> : " · No preset applied by the backend yet."}
                  {" "}Sent as <code className="text-slate-300">caption_style: &quot;{captionStyle}&quot;</code> when you re-render.
                </p>
              </div>

              {/* Phase 1 — Multiple editing styles. Sent as `style` on re-render. */}
              <div>
                <label className="block text-sm text-slate-300 mb-1">Editing style</label>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {EDITING_STYLES.map((s) => (
                    <button key={s.value} type="button" onClick={() => setStyle(s.value)}
                      aria-pressed={style === s.value}
                      className={`min-h-[44px] text-left px-3 py-2.5 rounded-xl border text-sm ${
                        style === s.value
                          ? "border-violet-400 bg-violet-600/20 text-white"
                          : "border-white/10 bg-ink text-slate-300 hover:border-white/25"
                      }`}>
                      <span className="block font-medium">{s.label}</span>
                      <span className="block text-xs text-slate-400 mt-0.5">{s.description}</span>
                    </button>
                  ))}
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  Selected: <span className="text-slate-300">{selectedStyle.label}</span> — {selectedStyle.description}
                  {" "}This style is sent to the backend as <code className="text-slate-300">style: &quot;{style}&quot;</code> when you re-render.
                </p>
              </div>

              {notice && <p className="text-sm text-emerald-300">{notice}</p>}
              <div className="flex flex-col sm:flex-row gap-2">
                <button onClick={save} disabled={saving} className="inline-flex min-h-[44px] items-center justify-center px-4 py-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm font-medium disabled:opacity-50">
                  {saving ? "Saving…" : "Save changes"}
                </button>
                <button onClick={reRender} disabled={rendering} className="inline-flex min-h-[44px] items-center justify-center px-4 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium disabled:opacity-50">
                  {rendering ? "Re-rendering…" : `Re-render (${selectedStyle.label})`}
                </button>
              </div>
            </section>

            <PublishApproval clipId={clip.id} clip={clip} caption={caption} hashtags={hashtagList} />
          </>
        )}
      </main>
    </>
  );
}
