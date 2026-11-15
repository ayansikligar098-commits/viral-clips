# Viral Clips — Backend

FastAPI + SQLAlchemy (SQLite dev / Postgres via `DATABASE_URL`), CPU-only.
See `../ARCHITECTURE.md` for the full design.

## Run

```bash
bash ../scripts/setup_backend.sh
.venv/bin/uvicorn app.main:app --port 8000
# health: curl http://localhost:8000/health
```

## Quality gate (hard rule)
Max 5 clips per video, default 3. A clip is rendered/published only if it
passes the gate in `app/services/scoring.py`: total ≥55, hook ≥12/25,
story completion ≥5/10, complete thought arc, high speech density,
word-level subtitles, contiguous window only (no splicing).

## Context-aware highlights
`app/services/context.py` segments the full transcript into topic segments
and complete thought arcs, scores setup→payoff / question→answer structure,
and expands a window 2–5s before the hook to keep setup context.
`Clip.context_preserved` + `context_reason` record the result per clip.

## Editing styles
`app/services/styles.py` — `STYLES` dict / `Style` dataclass / `get_style()`.
Presets: Podcast, Gaming, Cinematic, Hormozi-inspired, Minimal Captions.
Each preset sets real FFmpeg/ASS parameters (font/size/colours, zoom,
cut pace, crop mode, extra filters). Add a style by adding one entry —
the pipeline/renderer never change. Selectable per clip via
`POST /api/clips/{id}/render` (`edit_style`, `caption_style`) and
`GET /api/clips/styles`. The render endpoint also accepts the aliases
`style` (= edit_style), `start_time`/`end_time` (= trim_start/trim_end).
`PATCH /api/clips/{id}` updates title/caption/hashtags/selected_caption/
selected_hook/cta/caption_style/edit_style (or `style` alias) and the
variation lists; `ClipOut` returns `title_variations`,
`caption_variations`, `hooks` + `hook_variations`, `selected_caption`,
`selected_hook`, `cta`, `detected_language` and `style` (= edit_style).
Publish accepts `instagram_account_id` (or `account_id`) and
`scheduled_at` (or `publish_at`).

## Face tracking (modular)
`app/services/tracking/base.py` defines the `Tracker` interface
(`detect_track(frame) -> TrackResult`). `rendering.py` calls only that
interface. v1: `tracking/implementations/haar_tracker.py` (OpenCV Haar).
Planned: YOLO/MediaPipe person tracker — same interface; register in
`base.get_tracker()` and set `TRACKER_NAME=yolo`. See
`tracking/implementations/README.md`.

## Instagram
Official Meta Graph API only, container → publish, approval-gated
(`approved=true` required). No token = publish returns
`simulated-pending` with "no Instagram token connected — publish queued,
not published". Production needs Meta App Review.

## Layout
- `app/core/` config, security (JWT+bcrypt, Fernet), database
- `app/models/` SQLAlchemy models
- `app/services/` transcription, scenes, scoring, context, styles,
  tracking, rendering, captions, metadata, instagram, analytics, storage
- `app/api/` auth, videos, jobs, clips, instagram, publish, analytics
- `app/workers/worker.py` DB-polling background worker; `run_job(job_id)`
  is importable for tests
