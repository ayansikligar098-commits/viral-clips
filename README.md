# AI Viral Clipping Automation Platform

Turn a long video (podcast / interview / gaming) into a few **high-quality**
9:16 Instagram Reels — automatically. Upload → AI analysis → best moments →
short clips with burned word-by-word captions → viral score → preview →
approval-gated Instagram publishing.

> **Main priority is clip QUALITY, not quantity.** The platform analyses the
> whole video and keeps only the strongest moments — **3–5 clips per video**,
> never 10–20 weak ones. Every clip must pass a hard quality gate (strong
> hook in the first 3s, complete thought arc, no unnecessary silence, synced
> word-level subtitles, speaker-centred 9:16 framing, no misleading cuts).
> See `ARCHITECTURE.md` §8. Returning 0 clips for a weak/speechless video
> is a correct outcome, not a failure.

Separate project — do not mix with Link To QR or NativeProof.

## Stack (verified on disk, 2026-11-15)

| Layer | Stack |
|---|---|
| Frontend | Next.js 14.2.18 + React 18.3.1 + TypeScript 5.5.4 (strict) + Tailwind 3.4.10 — no plain-HTML pages |
| Backend | Python 3.12, FastAPI 0.115.6 + SQLAlchemy 2.0.36 + JWT/bcrypt |
| Video/AI | FFmpeg 8.1.2, faster-whisper 1.2.1 (`tiny`, CPU), PySceneDetect, OpenCV Haar (via swappable Tracker interface) |
| Dev infra | SQLite + DB-polling background worker + local storage (`backend/storage/`) |
| Prod infra | PostgreSQL + Redis + S3 via `DATABASE_URL` / env — same interfaces (see `ARCHITECTURE.md` §3) |

## Quick start

### Backend

```bash
cd backend
bash ../scripts/setup_backend.sh   # creates .venv, installs requirements
cp .env.example .env               # then set a real SECRET_KEY + FERNET_KEY
# generate keys:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
.venv/bin/uvicorn app.main:app --port 8000 --host 127.0.0.1
# → http://127.0.0.1:8000/health  {"status":"ok","service":"viral-clips-backend"}
# API docs: http://127.0.0.1:8000/docs
```

Notes:
- `WHISPER_MODEL=tiny` by default (CPU). Use `base` for better Hindi/
  Hinglish accuracy (slower). First run downloads the ~75 MB model to
  `~/.cache/huggingface`.
- **Known dependency fix (2026-11-15):** `requirements.txt` must include
  `requests` (faster-whisper import fails without it) and faster-whisper
  1.2.1. `transcription.py` also contains a compatibility shim: PyAV ≥ 15
  removed the `metadata_errors` kwarg that faster-whisper passes to
  `av.open()` — without the shim every transcription fails and the
  pipeline falls back to no-transcript mode (0 clips pass the gate).
- Never commit a real `.env` (it is gitignored). No secrets in frontend code.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev            # → http://localhost:3000
npm run build          # production build (verified: 15/15 routes)
```

Pages: Dashboard, Upload, Analysis, Clips, Clip Editor, Viral Score,
Instagram Accounts, Publishing Calendar, Analytics, Project History,
Settings, Login, Register.

## End-to-end workflow (all real, no fake buttons)

```
Long video → Upload (owns_content attestation required, 2 GB / 3 h limits)
  → Job queued → probe → Whisper transcribe (word timestamps, language detect)
  → scenes + silence → context-aware candidates (contiguous 20–60 s windows)
  → explainable viral score /100 + quality gate → keep top 3–5
  → FFmpeg render: 9:16 smart crop, loudnorm, burned word-by-word ASS captions
  → auto title (3 variations) / caption (3) / hooks (3+) / hashtags (8–12) / CTA / cover
  → Preview & edit in Clip Editor → Approve → Instagram publish / schedule
  → Analytics (real DB data only — empty state until a clip is published)
```

## Fully automated per clip (no manual writing required)

- Word-by-word animated subtitles from Whisper timestamps, important words
  highlighted in a different colour/bold.
- Punctuation + capitalisation restored by a real normaliser
  (`backend/app/services/text_norm.py`); Hinglish preserved as spoken.
- Titles (hook-first, ≤ 60 chars, 3 variations), Instagram captions
  (3 variations, 2–3 lines + CTA), hashtags (8–12), hooks (3+), CTA chosen
  by clip type, 1080×1920 cover (real ffmpeg frame).
- Hindi / English / Hinglish with automatic language detection
  (`detected_language` stored per video and clip). Devanagari subtitles use
  Noto Sans Devanagari when present.
- Subtitle presets (real ASS styles): Bold Yellow, White Minimal, Neon,
  Hormozi-style. Editing styles (real FFmpeg params): Podcast, Gaming,
  Cinematic, Hormozi-inspired, Minimal Captions.
- Editing is optional: editor fields are pre-filled, editable, saved via
  `PATCH /api/clips/{id}`, and the **edited version is what gets published**.

## API (base `http://localhost:8000`)

| Endpoint | Notes |
|---|---|
| `GET /health` | `{"status":"ok"}` |
| `POST /api/auth/register`, `POST /api/auth/login` | JWT (119-char token); bad token → 401 |
| `POST /api/videos/upload` (multipart) | `file` + `owns_content=true`; ffprobe metadata; returns `video` + `job_id` |
| `GET /api/videos`, `GET /api/videos/{id}` | |
| `GET /api/jobs/{id}` | real progress % + stage; poll every few seconds |
| `GET /api/clips?video_id=`, `GET /api/clips/{id}` | score, 7-factor breakdown + reasons, quality-gate status, `context_reason`, `context_preserved`, titles/captions/hooks/hashtags/CTA, `detected_language` |
| `PATCH /api/clips/{id}` | edit title/caption/hashtags/selected_caption/selected_hook/cta/style/caption_style |
| `POST /api/clips/{id}/render` | trim (`trim_start`/`trim_end` or `start_time`/`end_time`), `style`/`edit_style`, `caption_style`; re-renders 720×1280 MP4 |
| `GET /api/clips/{id}/file`, `GET /api/clips/{id}/cover` | serve MP4 / 1080×1920 JPG |
| `GET /api/clips/styles`, `GET /api/clips/caption-presets` | |
| `GET /api/instagram/connect` | Meta OAuth URL builder (see `docs/SETUP.md`) |
| `GET /api/instagram/callback`, `GET /api/instagram/accounts` | encrypted token storage |
| `POST /api/publish` | **requires `approved=true`** (else 403); no token → `simulated-pending` (never silent); `publish_at`/`scheduled_at` → queued, worker publishes at time |
| `GET /api/analytics`, `GET /api/analytics/summary` | real DB rows only; empty state otherwise — no mock analytics |

## Verified test evidence (2026-11-15, this VM)

Sample videos (real TTS speech, generated with gTTS — see `sample/`):

- `sample/sample_podcast_en.mp4` — English podcast, 250.6 s, 1280×720, H.264 + AAC
- `sample/sample_podcast_hi.mp4` — Hindi podcast, 156.5 s, 1280×720, H.264 + AAC

Pipeline runs (live server, JWT auth):

| Run | Video | Transcript | Candidates | Passed gate | Kept |
|---|---|---|---|---|---|
| Job 2 | EN 250 s | 500 words, `en` | 10 | 5 | **3** — scores 76.5 / 75.5 / 71.1 |
| Job 3 | HI 157 s | 300 words, `hi` | 6 | 1 | **1** — score 63.0 |
| Job 4 | EN re-run | 500 words, `en` | 10 | 5 | **3** — same 3 clips |
| Job 5 | HI re-run | 300 words, `hi` | 6 | 1 | **1** — score 63.0 |
| Job 1 | EN (before transcription fix) | 0 words (dependency bug) | 6 | 0 | **0 — correct gate behaviour** |

Rendered clips (all verified with `ffprobe` — 720×1280, H.264 + AAC, 9:16):

- `backend/storage/clips/job2_clip1.mp4` — 25.9 s, 686 KB, score 76.5
- `backend/storage/clips/job2_clip2.mp4` — 20.8 s, 587 KB, score 75.5
- `backend/storage/clips/job2_clip3.mp4` — 22.9 s, 621 KB, score 71.1
- `backend/storage/clips/job3_clip1.mp4` — 21.0 s, 498 KB, Hindi, score 63.0
- `backend/storage/clips/job4_clip1.mp4` — 25.9 s; `job4_clip2/3.mp4` — same 3 EN clips
- `backend/storage/clips/clip_5_Gaming.mp4` — re-render, Gaming + Neon, trimmed to 25.0 s, 672 KB
- Covers: `backend/storage/covers/job*_clip*.jpg` — 1080×1920 each
- Burned captions verified visually from extracted frames: word-by-word,
  current word highlighted yellow (Bold Yellow) / green (Neon), important
  words coloured + bold. Hindi clip frame shows Devanagari slide title and
  Roman-Hindi captions (see Limitations).

Example auto-generated metadata (clip 1, EN, score 76.5):
- Title: “What is the secret to going viral on Instagram?” (+ 2 variations)
- Caption: “What is the secret to going viral on Instagram?\nHere is the truth
  nobody tells you about the first three seconds.\nComment your answer below 👇”
- Hashtags: `#hook #secret #viral #instagram #truth #nobody #wasted #completely #reels #viralreels`
- Hooks: 3 variations; CTA: “Comment your answer below 👇”
- Score breakdown: Hook 19/25, Retention 11.5/20, Interestingness 15/15,
  Emotional 9/15, Story 10/10, Shareability 10/10, Replay 2/5 — with a
  reason for every factor; `context_preserved: true`.

Also verified live: register/login, bad-token 401, upload + ffprobe metadata,
job progress polling, PATCH edit persisted, re-render (Gaming/Neon),
publish without approval → **403**, approved without token →
`simulated-pending` (“no Instagram token connected — publish queued, not
published”), scheduled publish (2099) → `queued`, analytics empty state
(“No analytics data yet — publish a clip first. No mock data is shown.”).
Frontend: `npx tsc --noEmit` exit 0, `npm run build` exit 0, 15/15 routes.

Run the unit smoke test (no server needed):

```bash
cd backend && .venv/bin/python ../tests/smoke_test.py
```

## What still needs a real Meta app / Postgres in production

- **Instagram publishing is NOT real without a Meta token/app.** No-token
  publishes return `simulated-pending`; with a token, Meta also requires a
  publicly reachable `video_url`, so a local file path will fail with the
  Graph API error stored on the job — never silently. See
  `docs/SETUP.md` for Meta App Review steps (`instagram_basic` +
  `instagram_content_publish`).
- **Postgres/Redis/S3:** dev uses SQLite + DB-polling worker + local disk.
  Production swaps via `DATABASE_URL` and the storage/queue adapters —
  same interfaces, no code change to the pipeline.
- **Secrets:** generate a real `SECRET_KEY` + `FERNET_KEY` per environment;
  never reuse the local dev values.

## Known limitations (honest)

- **Hindi/Hinglish transcription (tiny model):** language is detected
  correctly (`hi`), but Whisper `tiny` romanises Hindi speech and mishears
  words (e.g. “sekundhi”, “tee kar te hai”), so Hindi captions are
  Roman-Hindi, not Devanagari, and Hindi hashtags can include misheard
  words. Use `WHISPER_MODEL=base` (or `small` on a bigger machine) for
  materially better Hindi accuracy.
- **Hashtag quality** is keyword-frequency based (English + Hindi stopword
  lists); it picks real content words but is not a semantic tagger.
- **Face tracking** is OpenCV Haar v1 behind a swappable `Tracker`
  interface (`backend/app/services/tracking/`); no face in the sample
  slides, so clips used the centre-crop fallback (correct behaviour).
- **Candidate windows can straddle a topic boundary** when thoughts run
  across segments (clip 3's caption mixes the end of one segment with the
  start of the next). Thoughts are complete, context is preserved, but
  topic-boundary enforcement is a Phase 2 improvement.
- **Punctuation restoration** is heuristic, not a neural model.
- **Caption font sizes** were reduced after visual inspection (Bold Yellow
  64→56 pt, Neon 68→60 pt, Hormozi 84→72 pt) so 4-word karaoke lines fit
  inside 720 px.
- Transcription is CPU-bound: ~250 s of audio took ~40 s with `tiny`
  once the model was cached; a 60-min podcast takes ~15–25 min.
  Jobs queue and show real progress; do not expect real-time on this VM.
