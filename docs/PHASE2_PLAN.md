# Phase 2 plan — draft for user decision (2026-11-15)

Phase 1 is built and verified (see README test evidence). This draft scopes
what comes next so the user can approve it in parts. Nothing here has been
built yet.

## Recommendation: try a real video first, then Phase 2

Reason: Phase 1 was tested only on synthetic slide samples
(`sample/sample_podcast_en.mp4`, 250 s; `sample/sample_podcast_hi.mp4`, 157 s)
with no faces — so face tracking used the centre-crop fallback, untested.
A real podcast/interview/gaming video will show whether topic-boundary
straddling, face framing, and Hindi captions actually hold up, before more
code is written on top of them.

### Try-it-first path (about 30 min, no new build)

```bash
cd ~/workspace/viral-clips/backend && bash ../scripts/setup_backend.sh
.venv/bin/uvicorn app.main:app --port 8000 --host 127.0.0.1
# second terminal:
cd ~/workspace/viral-clips/frontend && npm run dev  # http://localhost:3000
```

Register in the UI, upload a real long video, watch job progress, open the
clips. Backend server is stopped now; files and test DB remain on disk.

Watch first: `backend/storage/clips/job2_clip1.mp4` — score 76.5/100,
0.0–25.8 s, “What is the secret to going viral on Instagram?” — the best
Phase 1 clip, to calibrate what “good” looks like in this build.

What to judge on the real video: hook in first 3 s, complete thought arc,
no mid-topic cut, speaker framing (not centre-crop), Hindi/Hinglish caption
accuracy, hashtag relevance.

## Phase 2A — Quality (buildable here, no new accounts)

1. Topic-boundary enforcement — candidate windows must not straddle a topic
   segment (`backend/app/services/context.py`: `segment_topics`,
   `thought_completeness`). Known Phase 1 limit: windows can occasionally
   straddle a topic boundary.
2. Better Hindi — switch `WHISPER_MODEL` from `tiny` to `base` in
   `backend/.env` (config default is `tiny`; only `tiny` is cached in
   `~/.cache/huggingface` as of 2026-11-15, so `base` needs a download and
   is slower on CPU). Fixes Roman-Hindi mishearing; language detection
   itself is already correct.
3. Semantic hashtags — replace frequency-based hashtags with topic-aware
   ones (known Phase 1 limit).

## Phase 2B / Phase 3 — Scale (needs a deployment decision first)

Per `ARCHITECTURE.md`, scale is Phase 3, not Phase 2: Postgres / Redis /
S3 via docker-compose, Celery workers, GPU worker.
Blocker verified 2026-11-15: Docker is **not installed** on this VM, no
`docker-compose` file exists in `~/workspace/viral-clips/`, and no
Postgres/Redis is installed. So this slice needs the user to choose:
install Docker/Postgres/Redis on this VM, or deploy to cloud — it cannot
be done silently as a code-only change. Interfaces already exist
(SQLite→Postgres via `DATABASE_URL`, local storage→S3 via the Storage
interface), so the code change is the swap, not a rewrite.

## Instagram real publishing — longest pole, user-owned

Publishing is `simulated-pending` without a Meta token; nothing real can
publish until (from `docs/SETUP.md`):
1. Meta app (Business) + Instagram Graph API product.
2. Instagram Professional account linked to a Facebook Page; add it as a
   test user in dev mode.
3. OAuth redirect `http://localhost:8000/api/instagram/callback`, scopes
   `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`;
   set `META_APP_ID` / `META_APP_SECRET` in `backend/.env`.
4. Meta App Review for those permissions (production).
5. Public clip URLs (S3) — local `backend/storage/` paths are rejected
   by Meta. This is why Phase 2B matters before real publishing.

## Decision asked of the user

- (a) Try a real video first (recommended), or
- (b) Start Phase 2A quality now, or
- (c) Start Phase 2B/Phase 3 scale — and if so, VM Docker install or cloud?
- (d) Start the Meta app / App Review steps in parallel (user-owned)?
