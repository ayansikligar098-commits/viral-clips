// Shared types — mirror the FastAPI backend models (ARCHITECTURE.md §3-§5).
// Never invent analytics or clips here; these are shapes for real API data only.

export interface User {
  id: string | number;
  email: string;
  name?: string | null;
  created_at?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type?: string;
  user?: User;
}

export interface Video {
  id: string | number;
  user_id?: string | number;
  title?: string | null;
  filename?: string | null;
  original_filename?: string | null;
  duration?: number | null;
  status?: string | null;
  created_at?: string | null;
  file_path?: string | null;
  source_url?: string | null;
}

export interface Job {
  id: string | number;
  video_id?: string | number | null;
  status: string;
  stage?: string | null;
  progress?: number | null;
  message?: string | null;
  error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export type ScoreFactorKey =
  | "hook_strength"
  | "retention_potential"
  | "interestingness"
  | "emotional_impact"
  | "story_completion"
  | "shareability"
  | "replay_potential";

export interface ScoreFactor {
  score: number;
  max?: number;
  reason: string;
}

export type ScoreBreakdown = Partial<Record<ScoreFactorKey, ScoreFactor>> & {
  [key: string]: ScoreFactor | undefined;
};

export const SCORE_FACTOR_LABELS: Record<string, string> = {
  hook_strength: "Hook strength (first 3s)",
  retention_potential: "Retention potential",
  interestingness: "Interestingness",
  emotional_impact: "Emotional impact",
  story_completion: "Story completion",
  shareability: "Shareability",
  replay_potential: "Replay potential",
};

export const SCORE_FACTOR_MAX: Record<string, number> = {
  hook_strength: 25,
  retention_potential: 20,
  interestingness: 15,
  emotional_impact: 15,
  story_completion: 10,
  shareability: 10,
  replay_potential: 5,
};

export interface WordTiming {
  word: string;
  start?: number | null;
  end?: number | null;
}

export interface Clip {
  id: string | number;
  video_id?: string | number | null;
  job_id?: string | number | null;
  title: string;
  caption?: string | null;
  hashtags?: string[] | string | null;
  hooks?: string[] | null;
  // Fully automated workflow — all optional, shown ONLY when the API
  // returns them. The frontend never invents titles / captions / hooks /
  // hashtags / language. When the backend does not return a field yet,
  // the corresponding section is omitted entirely.
  // Auto-generated variations (backend metadata service produces 3 titles,
  // 3 captions, 3 hooks; see ARCHITECTURE.md §5).
  title_variations?: string[] | string | null;
  titles?: string[] | string | null;
  caption_variations?: string[] | string | null;
  captions?: string[] | string | null;
  hook_variations?: string[] | string | null;
  selected_caption?: string | null;
  selected_hook?: string | null;
  cta?: string | null;
  detected_language?: string | null;
  language?: string | null;
  // Word-by-word subtitle timings, when the API returns them (transcription
  // words for this clip's window). Omitted when absent — never fabricated.
  words?: WordTiming[] | null;
  subtitle_words?: WordTiming[] | null;
  transcript_words?: WordTiming[] | null;
  subtitle_preview?: string | null;
  start_time?: number | null;
  end_time?: number | null;
  start?: number | null;
  end?: number | null;
  duration?: number | null;
  viral_score?: number | null;
  score?: number | null;
  score_breakdown?: ScoreBreakdown | null;
  quality_gate_passed?: boolean | null;
  quality_gate_failures?: string[] | null;
  status?: string | null;
  file_path?: string | null;
  cover_path?: string | null;
  caption_style?: string | null;
  // Phase 1 — context-aware highlights (ARCHITECTURE §4, Phase 1 addendum).
  // Shown ONLY when the backend returns them; never invented in the UI.
  // Examples the backend may return: "setup → payoff", "question → answer",
  // "story arc: problem → resolution".
  context_reason?: string | null;
  selection_reason?: string | null;
  context?: string | null;
  context_preserved?: boolean | null;
  // Phase 1 — editing style (see EDITING_STYLES below). Backend-driven;
  // the frontend sends it as `style` on re-render and never assumes a value.
  style?: string | null;
  editing_style?: string | null;
  created_at?: string | null;
}

// Phase 1 — multiple editing styles. The `value` is sent verbatim as `style`
// in POST /api/clips/{id}/render. Descriptions are UI copy for the preset,
// not claims about the render — framing/captions are backend-driven.
export interface EditingStyle {
  value: string;
  label: string;
  description: string;
}
export const EDITING_STYLES: EditingStyle[] = [
  { value: "podcast", label: "Podcast", description: "Calm, speaker-framed cuts for interviews and conversations." },
  { value: "gaming", label: "Gaming", description: "Fast, punchy cuts with energetic pacing for gameplay moments." },
  { value: "cinematic", label: "Cinematic", description: "Slower, dramatic pacing with emphasis on visual moments." },
  { value: "hormozi", label: "Hormozi-inspired", description: "Direct, high-energy hook-first cuts in the Alex Hormozi style." },
  { value: "minimal", label: "Minimal Captions", description: "Clean, understated captions and restrained editing." },
];

// The clip's context/reason, from the API only. Returns null when the
// backend did not provide one — the UI then omits the section entirely.
export function clipContextReason(c: Clip): string | null {
  return c.context_reason ?? c.selection_reason ?? c.context ?? null;
}

export function clipScore(c: Clip): number | null {
  return c.viral_score ?? c.score ?? null;
}
export function clipStart(c: Clip): number | null {
  return c.start_time ?? c.start ?? null;
}
export function clipEnd(c: Clip): number | null {
  return c.end_time ?? c.end ?? null;
}
export function clipHashtags(c: Clip): string[] {
  if (!c.hashtags) return [];
  if (Array.isArray(c.hashtags)) return c.hashtags;
  return c.hashtags.split(/[,\s]+/).filter(Boolean);
}

// Normalise a field that may arrive as a string, a string array, or null.
export function asStringArray(v: string[] | string | null | undefined): string[] {
  if (!v) return [];
  if (Array.isArray(v)) return v.filter(Boolean);
  return v.split(/\n+/).map((s) => s.trim()).filter(Boolean);
}

// Auto-generated variations — API only, empty when the backend has not
// returned them yet. Hook variations fall back to `hooks` (the same list
// the backend already returns).
export function clipTitleVariations(c: Clip): string[] {
  return asStringArray(c.title_variations ?? c.titles);
}
export function clipCaptionVariations(c: Clip): string[] {
  return asStringArray(c.caption_variations ?? c.captions);
}
export function clipHookVariations(c: Clip): string[] {
  return asStringArray(c.hook_variations ?? c.hooks);
}
// The caption / hook the publish flow must use: the saved selection first,
// then the clip caption / first hook. Never invented.
export function clipSelectedCaption(c: Clip): string | null {
  return c.selected_caption ?? c.caption ?? null;
}
export function clipSelectedHook(c: Clip): string | null {
  return c.selected_hook ?? clipHookVariations(c)[0] ?? null;
}
export function clipDetectedLanguage(c: Clip): string | null {
  return c.detected_language ?? c.language ?? null;
}
export function clipWords(c: Clip): WordTiming[] {
  return c.words ?? c.subtitle_words ?? c.transcript_words ?? [];
}

// Subtitle (caption) presets — DISTINCT from the editing styles above
// (Podcast / Gaming / Cinematic / Hormozi-inspired / Minimal Captions).
// The preset `value` is sent verbatim as `caption_style` in
// POST /api/clips/{id}/render. Descriptions are UI copy only.
export interface CaptionPreset {
  value: string;
  label: string;
  description: string;
}
export const CAPTION_PRESETS: CaptionPreset[] = [
  { value: "Bold Yellow", label: "Bold Yellow", description: "Big bold yellow-highlighted words, high contrast." },
  { value: "White Minimal", label: "White Minimal", description: "Clean white words, understated, no heavy outline." },
  { value: "Neon", label: "Neon", description: "Bright neon-highlighted words for high-energy clips." },
  { value: "Hormozi-style", label: "Hormozi-style", description: "Huge bold captions, direct-to-camera punch." },
];

// Resolve what the backend stored as `caption_style` onto a preset value.
// Legacy values the backend has stored ("Bold" / "Minimal" / "Neon") map
// onto their nearest preset; an unknown value returns null so the UI
// shows the stored value as-is instead of guessing a preset.
export function resolveCaptionPreset(stored: string | null | undefined): string | null {
  if (!stored) return null;
  const hit = CAPTION_PRESETS.find((p) => p.value.toLowerCase() === stored.toLowerCase());
  if (hit) return hit.value;
  const legacy: Record<string, string> = {
    bold: "Bold Yellow",
    minimal: "White Minimal",
    neon: "Neon",
    hormozi: "Hormozi-style",
    "hormozi-inspired": "Hormozi-style",
  };
  return legacy[stored.toLowerCase()] ?? null;
}

export interface InstagramAccount {
  id: string | number;
  username?: string | null;
  account_id?: string | number | null;
  account_type?: string | null;
  connected?: boolean;
  created_at?: string | null;
}

export interface PublishJob {
  id: string | number;
  clip_id?: string | number | null;
  clip_title?: string | null;
  status: string;
  scheduled_at?: string | null;
  published_at?: string | null;
  permalink?: string | null;
  media_id?: string | null;
  error?: string | null;
  created_at?: string | null;
}

export interface AnalyticsSummary {
  total_views?: number | null;
  total_reach?: number | null;
  total_likes?: number | null;
  total_comments?: number | null;
  total_shares?: number | null;
  total_saves?: number | null;
  clips_published?: number | null;
  per_clip?: Array<{
    clip_id: string | number;
    title?: string | null;
    views?: number | null;
    reach?: number | null;
    likes?: number | null;
    comments?: number | null;
    shares?: number | null;
    saves?: number | null;
  }>;
  [key: string]: unknown;
}

export interface AnalysisResult {
  video_id?: string | number;
  transcript?: string | null;
  transcript_text?: string | null;
  scenes?: Array<{ start?: number; end?: number; description?: string | null }> | null;
  summary?: string | null;
  duration?: number | null;
}
