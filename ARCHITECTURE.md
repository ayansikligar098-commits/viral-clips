# AI Viral Clipping Automation Platform — Architecture & Roadmap

Separate project. Do NOT mix with Link To QR or NativeProof.

## 1. Environment inspected — 2026-11-15

| Item | Found in this VM | Implication |
|---|---|---|
| Python | 3.12.3 | FastAPI backend OK |
| Node / npm | 24.22.1 / 10.9.4 | Next.js 14+ OK |
| FFmpeg | 8.1.2, libx264, libass, libfreetype | Clipping, 9:16 crop, burned captions OK |
| CPU / RAM / Disk | 4 vCPU, 7.7 GB RAM, 149 GB free | CPU-only inference, no GPU |
| GPU | None | Use `faster-whisper` tiny/base, not large; no CUDA |
| Postgres / Redis / Docker | Not installed | **Local dev: SQLite + file queue + local storage. Production: Postgres + Redis + S3 — same interfaces, swapped by env.** This is the one deliberate alternative, explained below. |
| Installed Python libs | numpy, pillow only | Install FastAPI, faster-whisper, PySceneDetect, opencv-python-headless in venv |
| Internet | Works | Model download + npm install OK |

## 2. End-to-end workflow (the success metric)

```
LONG VIDEO (upload / URL)
  → Upload service (chunked, resumable, virus/size checks, ownership attestation)
  → Job queued (Redis RQ / Celery in prod; SQLite job table + background worker locally)
  → 1. Probe (ffprobe: duration, fps, resolution, audio)
  → 2. Transcribe (faster-whisper, word timestamps, language detect)
  → 3. Scene detect (PySceneDetect ContentDetector) + silence detect (ffmpeg silencedetect)
  → 4. Moment scoring (see §4) → candidate windows 20–60s, hook in first 3s
  → 5. Face / speaker tracking (OpenCV Haar + centroid tracking, fallback centre-crop)
  → 6. Render clips: 9:16 crop + smart reframe, zoom/cuts, silence trim, loudnorm, burned word-by-word ASS captions
  → 7. Metadata: title, caption, hashtags, hooks, cover frame (ffmpeg thumbnail)
  → 8. Viral score /100 + reasons
  → Preview in Clip Editor (trim, caption style, re-render)
  → User APPROVES → Instagram publish (or schedule)
  → Analytics ingest (Graph API insights) → feedback loop re-weights scoring
```

Never publish without explicit user approval. Never guarantee virality.

## 3. System architecture

```
┌──────────────── Next.js 14 (App Router, TS, Tailwind, dark SaaS) ────────────────┐
│ Dashboard · Upload · Analysis · Clips · Clip Editor · Viral Score · Instagram │
│ Accounts · Publishing Calendar · Analytics · Project History · Settings        │
└───────────────▲ REST /api/* (JWT) ────────────────┬────────────────────────────┘
┌───────────────┴────────────────────────────────────┴────────────────────────────┐
│ FastAPI (Python 3.12)                                                            │
│ /auth /videos /jobs /clips /captions /instagram /publish /analytics /settings   │
│ Auth: JWT + bcrypt, RBAC ready. Secrets only in env / server, never frontend.  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Services: transcription.py · scenes.py · scoring.py · rendering.py (FFmpeg)    │
│           captions.py · metadata.py · instagram.py · analytics.py · storage.py  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Workers: background job runner (thread pool locally, Celery+Redis in prod)     │
│   progress via polling + SSE, retry with backoff, dead-letter on 3 failures     │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Data: SQLite (dev) / PostgreSQL (prod) via SQLAlchemy — same models            │
│ Queue: DB job table (dev) / Redis (prod) — same Job interface                   │
│ Storage: local ./storage (dev) / S3-compatible (prod) — same Storage interface  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Key design decisions
- **Adapter pattern for DB/Queue/Storage:** one interface, two implementations. Lets the product actually run and be tested here, and deploy unchanged to Postgres/Redis/S3.
- **CPU-first AI:** `faster-whisper` (CTranslate2, tiny/base) + PySceneDetect + OpenCV Haar. No GPU needed, cost stays low. Optional upgrade path: Whisper large-v3 on GPU worker, or cloud transcription, behind the same `Transcriber` interface.
- **Scoring is explainable, not magic:** weighted, measurable signals (§4). No mock analytics — analytics only from real Graph API data or clearly labelled “no data yet”.
- **Instagram via official Meta Graph API only:** Facebook Login / Instagram Login, `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`. Reels publishing is container → publish, with status polling. Requires Meta App Review for production; dev mode works with test users. Scheduling is our DB + worker, not Meta (Meta has no native Reels scheduling).
- **Copyright / ownership:** upload requires attestation, only user-owned / licensed content, no YouTube-download bypass. Supported sources: direct upload + public direct video URLs the user owns.

## 4. Viral scoring — /100, explainable

Weights (v1, tuned by real analytics later):
- Hook strength, first 3s — 25 (question / surprise / strong claim / emotion word in transcript, loudness onset, face on screen)
- Retention potential — 20 (speech density, no long silence, scene changes, topic continuity)
- Interestingness — 15 (novelty keywords, laughter / emphasis, named entities, contrast)
- Emotional impact — 15 (sentiment lexicon, exclamation, pitch/energy proxy, laughter)
- Story completion — 10 (complete sentence / thought arc inside window)
- Shareability — 10 (quotable line, relatable / controversial-but-not-misleading, call-to-share language)
- Replay potential — 5 (dense punchline, fast payoff, loop-friendly ending)

Each clip stores `score_breakdown: {factor: {score, reason}}`. UI shows the reasons, never a bare number.

## 5. Captions & metadata
- Word-by-word ASS subtitles, highlighted word, karaoke-style, 3 style presets (Bold, Minimal, Neon).
- Titles: hook-first, ≤60 chars, 3 variations. Captions: 2–3 lines + CTA. Hashtags: from transcript keywords + niche tags, max 8–12. Cover: best face / high-contrast frame at 1s in.

## 6. Instagram integration (approval-gated)
1. Connect Professional account → OAuth → long-lived token (encrypted at rest, refresh job).
2. Pick clip → edit caption/cover → Approve → Create media container → Poll status → Publish → Store media ID, permalink, status.
3. Schedule: `publish_at` in DB, worker publishes at time, failure → retry once → mark failed with Meta error, never silent-fail.
4. History + analytics: views/reach/likes/comments/shares/saves via `/insights` where available.

## 7. Roadmap

**Phase 1 — Working core (this build):** scaffold, auth, upload, job pipeline, transcription, scoring, FFmpeg render, clips list, preview, editor (trim/caption style), viral score UI, Instagram connect + manual publish (approval-gated), calendar, analytics page (real data or empty state).
**Phase 2 — Polish:** face tracking smoothing, zoom presets, music bed, multi-variation renders, A/B hooks.
**Phase 3 — Scale:** Postgres/Redis/S3 via docker-compose, Celery workers, GPU worker, cost guardrails, subscription (Stripe-ready architecture: plans table, usage quotas, webhook stub).
**Phase 4 — Learning loop:** analytics-weighted re-scoring, per-account best-time suggestions.

## 8. Quality gate — quality over quantity (hard rule)

**Main priority is clip quality, not quantity.** Never generate random
clips just to produce 10–20. Analyse the complete video, understand its
context, rank genuinely engaging moments, and keep only the strongest —
**3–5 clips per long video** (`MAX_CLIPS_PER_VIDEO=5`,
`DEFAULT_CLIPS_PER_VIDEO=3`). Fewer, better clips is the correct outcome;
returning 0 clips for a weak/speechless video is valid, not a failure.

Enforced in `backend/app/services/scoring.py` (`rank_candidates()` keeps
only gate-passing candidates, ranked by score) and in the worker
(`backend/app/workers/worker.py`), which never pads with weak clips.
A candidate passes only if **all** of these hold:

- **Strong opening hook in the first 3 seconds** — hook factor ≥ 12/25
  (question / surprise / strong claim / emotion word in the first 3s).
- **Meaningful beginning and ending** — complete thought/sentence arc,
  no mid-sentence cuts (story completion ≥ 5/10, `thought_completeness()`).
- **No unnecessary silence** — speech density ≥ 0.4, silence ratio ≤ 35%,
  silence-trimmed edges.
- **Proper subtitles** — word-level, synced transcript words must exist
  for the window (no transcript → no clip).
- **Correct speaker framing** — face/speaker-centred 9:16 crop via the
  Tracker interface, centre-crop fallback; framing recorded per clip.
- **No misleading cuts** — contiguous windows only; never splice
  non-adjacent segments; original context preserved (`context_preserved`).
- **Total score ≥ 55/100** (explainable breakdown, §4).

Each clip stores `quality_gate_passed` + `quality_gate_failures` (list of
reasons) and the UI shows the gate status and reasons, never a bare score.
Verified 2026-11-15 on real spoken samples: English 250s video → 10
candidates, 5 passed, kept 3 (scores 76.5 / 75.5 / 71.1); Hindi 157s video
→ 6 candidates, 1 passed, kept 1 (score 63.0); a speechless test video →
0 passed, 0 clips (correct).

## 9. Context-aware highlight detection (Phase 1)

Clips are NOT selected on keywords / loudness / scene changes alone.
`backend/app/services/context.py` uses the full transcript:
- **Topic segmentation** — groups thoughts into topic segments (long gaps,
  setup markers, question openings).
- **Thought-boundary detection** — a thought is a run of words ending at
  sentence punctuation or a long pause; candidates must start/end on
  thought boundaries (no mid-sentence cuts).
- **Context scoring** — a candidate is scored on conversational context:
  setup → payoff, question → answer, multi-thought story arc.
- **Context window expansion** — where the hook's setup sits just before
  it, the window is expanded 2–5s backwards to include it.
- **Contiguous windows only** — never splice non-adjacent segments.
Each clip stores `context_preserved` (bool) + `context_reason`, and the
context score feeds the Story completion factor (10/100) in `scoring.py`.
v1 uses lexical heuristics; a later embedding-based segmenter can replace
`segment_topics()` behind the same return shape.

## 10. Multiple editing styles (Phase 1)

Rendering is style-driven from the start: `backend/app/services/styles.py`
defines a `Style` dataclass + `STYLES` registry + `get_style()`.
Presets: **Podcast, Gaming, Cinematic, Hormozi-inspired, Minimal Captions**.
Each preset sets REAL FFmpeg/ASS parameters — caption font/size/colour/
position, zoom punch-in factor, cut pace, crop behaviour, extra filters
(e.g. saturation/contrast), loudnorm target — not just a label.
Selectable per clip via `POST /api/clips/{id}/render`
(`edit_style`, `caption_style`) and listed at `GET /api/clips/styles`.
New styles are added as one entry in `STYLES` (or `register_style()`);
the core pipeline and renderer never change.

## 11. Modular face tracking (Phase 1)

`backend/app/services/tracking/base.py` defines the `Tracker` interface:
`detect_track(frame) -> TrackResult` (bbox / centre_x / centre_y).
`rendering.py` calls ONLY this interface, never Haar directly.
- v1: `tracking/implementations/haar_tracker.py` — OpenCV Haar cascade,
  largest face + centroid smoothing, centre-crop fallback.
- Planned: YOLO / MediaPipe person-detection tracker — same interface,
  largest *person* bbox. To swap: add the implementation file, register
  it in `base.get_tracker()`, set `TRACKER_NAME=yolo` (env). No renderer
  change needed. See `tracking/implementations/README.md`.

## 12. Fully automated workflow (Phase 1)

Every generated clip automatically includes, with no manual writing:
1. Word-by-word animated subtitles (Whisper word timestamps, burned via ASS).
2. Highlighted important words (keyword/emotion words in a different
   colour + bold in the ASS line).
3. Proper punctuation/capitalisation — `backend/app/services/text_norm.py`
   (heuristic sentence-case + terminal-punctuation restoration; NOT a
   neural punctuation model, documented as such). Raw lowercase Whisper
   text is never shipped.
4. Viral-style title, hook-first, ≤60 chars, 3 variations
   (`title_variations`, default pre-selected).
5. Engaging Instagram caption, 2–3 lines + CTA, 3 variations
   (`caption_variations`, `selected_caption` pre-selected).
6. Hashtags from transcript keywords + niche tags, 8–12.
7. Strong opening hook (first 3s), 3+ hook variations.
8. Reel cover — real ffmpeg frame ~1s in, scaled/cropped to 1080×1920.
9. CTA chosen by clip type (question → comment, how-to → save/share,
   story → follow).
10. Editor: `PATCH /api/clips/{id}` updates title/caption/hashtags/
    selected_caption/selected_hook/cta; the SAVED version is what publish
    uses (`app/services/publishing.py: build_publish_caption` appends
    hashtags automatically).
- Languages: Whisper auto-detects language, stored per Video and per Clip
  (`detected_language`: en / hi / hinglish). Hinglish (Roman Hindi) is
  preserved as spoken, never translated; Devanagari Hindi uses
  Noto Sans Devanagari (present on this VM) in ASS, falling back to
  DejaVu Sans with a log line.
- Subtitle presets (distinct from editing styles): Bold Yellow,
  White Minimal, Neon, Hormozi-style — real ASS font/size/colour/
  animation changes, selectable per clip via `caption_style`
  (`GET /api/clips/caption-presets`, `POST /api/clips/{id}/render`).
- Scheduled publishing: `publish_at` / `scheduled_at` on PublishJob;
  the worker's `check_due_publish_jobs()` publishes due approved jobs
  and records status; no token → `simulated-pending`, never silent-fail.

## 13. Costs & limits (honest)
- CPU whisper base ≈ 0.3–0.5× realtime on this VM; a 60-min podcast ≈ 20–30 min transcribe. Keep clips ≤60s, queue jobs, show real progress.
- No GPU here — do not claim real-time large-model analysis.
- Instagram Reels: ≤90s, 9:16, MP4 H.264, ≤250MB in practice; we enforce at render.
