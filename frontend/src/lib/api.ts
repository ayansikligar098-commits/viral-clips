// Typed fetch client for the FastAPI backend (ARCHITECTURE.md §3).
// Base URL comes only from NEXT_PUBLIC_API_URL. JWT is stored in localStorage
// after login/register; it is never hardcoded and never logged.
import type {
  AnalysisResult,
  AnalyticsSummary,
  AuthResponse,
  Clip,
  InstagramAccount,
  Job,
  PublishJob,
  User,
  Video,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL === "relative"
    ? "" // Single-URL mode: /api/* is proxied by Next.js rewrites (see
         // next.config.js, NEXT_REWRITE_TO_BACKEND=1). Used by the free
         // tunnel test so one public HTTPS URL serves frontend + backend.
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const TOKEN_KEY = "viral_clips_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}
export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}
export function isLoggedIn(): boolean {
  return Boolean(getToken());
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail))
      return data.detail.map((d: { msg?: string }) => d.msg || "Validation error").join("; ");
    if (typeof data?.message === "string") return data.message;
    return `Request failed (${res.status})`;
  } catch {
    return `Request failed (${res.status})`;
  }
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> | undefined),
  };
  const isForm = init.body instanceof FormData;
  if (!isForm && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

// Accept either a bare array or a wrapped {items|results|data|videos|clips} payload.
export function asArray<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data as T[];
  if (data && typeof data === "object") {
    const o = data as Record<string, unknown>;
    for (const k of ["items", "results", "data", "videos", "clips", "jobs", "accounts", "publish_jobs"]) {
      if (Array.isArray(o[k])) return o[k] as T[];
    }
  }
  return [];
}

export function clipFileUrl(clip: Clip): string {
  return `${API_URL}/api/clips/${clip.id}/file`;
}
export function clipCoverUrl(clip: Clip): string {
  return clip.cover_path
    ? `${API_URL}/api/clips/${clip.id}/cover`
    : clipFileUrl(clip);
}
// Cover thumbnail (1080x1920, from GET /api/clips/{id}/cover). Returns null
// when the backend has not produced a cover — callers must omit the <img>
// then, never fall back to the video file as an image.
export function clipCoverUrlOrNull(clip: Clip): string | null {
  return clip.cover_path ? `${API_URL}/api/clips/${clip.id}/cover` : null;
}
export function videoFileUrl(video: Video): string {
  return `${API_URL}/api/videos/${video.id}/file`;
}

// --- Auth ---
export async function login(email: string, password: string): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (data.access_token) setToken(data.access_token);
  return data;
}
export async function register(
  email: string,
  password: string,
  name?: string,
): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
  if (data.access_token) setToken(data.access_token);
  return data;
}
export async function getMe(): Promise<User> {
  return apiFetch<User>("/api/auth/me");
}
export function logout() {
  clearToken();
}

// --- Videos & upload ---
export async function listVideos(): Promise<Video[]> {
  return asArray<Video>(await apiFetch("/api/videos"));
}
export async function getVideo(id: string | number): Promise<Video> {
  return apiFetch<Video>(`/api/videos/${id}`);
}
export async function uploadVideo(
  file: File,
  opts: { title?: string; sourceUrl?: string; ownsContent?: boolean; onProgress?: (pct: number) => void } = {},
): Promise<Video> {
  // XHR is used so upload progress can be reported; fetch has no upload progress.
  const token = getToken();
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    if (opts.title) form.append("title", opts.title);
    // Backend requires owns_content=true (400 otherwise). The UploadForm
    // only enables submit after the ownership checkbox is ticked.
    if (opts.ownsContent) form.append("owns_content", "true");
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/api/videos/upload`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && opts.onProgress)
        opts.onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          // Backend returns {video: {...}, job_id} — unwrap to the video.
          const data = JSON.parse(xhr.responseText) as Video & { video?: Video };
          resolve((data.video ?? data) as Video);
        } catch {
          reject(new Error("Upload succeeded but the response was not valid JSON."));
        }
      } else {
        try {
          const d = JSON.parse(xhr.responseText);
          reject(new Error(typeof d?.detail === "string" ? d.detail : `Upload failed (${xhr.status})`));
        } catch {
          reject(new Error(`Upload failed (${xhr.status})`));
        }
      }
    };
    xhr.onerror = () => reject(new Error("Upload failed: could not reach the API. Is the backend running?"));
    xhr.send(form);
  });
}
export async function uploadVideoByUrl(sourceUrl: string, title?: string): Promise<Video> {
  return apiFetch<Video>("/api/videos/upload-url", {
    method: "POST",
    body: JSON.stringify({ source_url: sourceUrl, url: sourceUrl, title }),
  });
}

// --- Jobs / analysis ---
export async function listJobs(): Promise<Job[]> {
  return asArray<Job>(await apiFetch("/api/jobs"));
}
export async function getJob(id: string | number): Promise<Job> {
  return apiFetch<Job>(`/api/jobs/${id}`);
}
export async function startAnalysis(videoId: string | number): Promise<Job> {
  return apiFetch<Job>(`/api/videos/${videoId}/analyze`, { method: "POST" });
}
export async function getAnalysis(videoId: string | number): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>(`/api/videos/${videoId}/analysis`);
}

// --- Clips ---
export async function listClips(videoId?: string | number): Promise<Clip[]> {
  const q = videoId ? `?video_id=${videoId}` : "";
  return asArray<Clip>(await apiFetch(`/api/clips${q}`));
}
export async function getClip(id: string | number): Promise<Clip> {
  return apiFetch<Clip>(`/api/clips/${id}`);
}
// Fully automated workflow: save the (edited or auto-generated) metadata.
// PATCH /api/clips/{id} with title / caption / hashtags plus the chosen
// caption, hook and CTA. The saved version is what the Publish flow uses.
// Fields are only sent when set — the backend is the source of truth and
// this client never invents values for fields the user did not pick.
export async function updateClip(
  id: string | number,
  patch: Partial<Clip> & {
    caption_style?: string;
    style?: string;
    editing_style?: string;
    selected_caption?: string | null;
    selected_hook?: string | null;
    cta?: string | null;
  },
): Promise<Clip> {
  return apiFetch<Clip>(`/api/clips/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}
// Phase 1: `style` is a real API parameter — one of the EDITING_STYLES values
// (podcast | gaming | cinematic | hormozi | minimal). It is sent verbatim as
// `style` in the re-render request; `editing_style` is kept as a fallback
// alias only for backends that expect that name. No tracking/framing
// assumptions are hardcoded here — framing is backend-driven.
// `caption_style` is the SUBTITLE preset (Bold Yellow | White Minimal |
// Neon | Hormozi-style) — distinct from the editing style above.
// The backend's RenderRequest also accepts trim_start / trim_end /
// edit_style, so those canonical keys are sent alongside the aliases.
export async function renderClip(
  id: string | number,
  opts: {
    start_time?: number;
    end_time?: number;
    trim_start?: number;
    trim_end?: number;
    caption_style?: string;
    style?: string;
    editing_style?: string;
    edit_style?: string;
  },
): Promise<Clip | Job> {
  const start = opts.start_time ?? opts.trim_start;
  const end = opts.end_time ?? opts.trim_end;
  const style = opts.style ?? opts.editing_style ?? opts.edit_style;
  const body: Record<string, unknown> = { ...opts };
  if (start !== undefined) {
    body.start_time = start;
    body.trim_start = start;
  }
  if (end !== undefined) {
    body.end_time = end;
    body.trim_end = end;
  }
  if (opts.caption_style !== undefined) body.caption_style = opts.caption_style;
  if (style) {
    body.style = style;
    body.editing_style = style;
    body.edit_style = style;
  }
  return apiFetch<Clip | Job>(`/api/clips/${id}/render`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
export async function deleteClip(id: string | number): Promise<void> {
  await apiFetch(`/api/clips/${id}`, { method: "DELETE" });
}

// --- Instagram & publishing ---
export async function listInstagramAccounts(): Promise<InstagramAccount[]> {
  return asArray<InstagramAccount>(await apiFetch("/api/instagram/accounts"));
}
export function instagramConnectUrl(): string {
  return `${API_URL}/api/instagram/connect`;
}
export async function disconnectInstagram(id: string | number): Promise<void> {
  await apiFetch(`/api/instagram/accounts/${id}`, { method: "DELETE" });
}
export async function publishClip(
  clipId: string | number,
  opts: {
    account_id?: string | number;
    instagram_account_id?: string | number;
    scheduled_at?: string | null;
    publish_at?: string | null;
    caption?: string;
    approved?: boolean;
  },
): Promise<PublishJob> {
  // Approval-gated: the backend requires approved=true (403 otherwise).
  // `scheduled_at` is the backend's field; `publish_at` is sent as the
  // same value so callers using the schedule name also work.
  const scheduledAt = opts.scheduled_at ?? opts.publish_at ?? null;
  const accountId = opts.instagram_account_id ?? opts.account_id;
  return apiFetch<PublishJob>("/api/publish", {
    method: "POST",
    body: JSON.stringify({
      clip_id: clipId,
      approved: opts.approved ?? true,
      instagram_account_id: accountId,
      account_id: accountId,
      scheduled_at: scheduledAt,
      publish_at: scheduledAt,
      caption: opts.caption,
    }),
  });
}
export async function listPublishJobs(): Promise<PublishJob[]> {
  return asArray<PublishJob>(await apiFetch("/api/publish"));
}
export async function getPublishJob(id: string | number): Promise<PublishJob> {
  return apiFetch<PublishJob>(`/api/publish/${id}`);
}

// --- Analytics & settings ---
export async function getAnalytics(): Promise<AnalyticsSummary> {
  return apiFetch<AnalyticsSummary>("/api/analytics");
}
export async function getSettings(): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/settings");
}
