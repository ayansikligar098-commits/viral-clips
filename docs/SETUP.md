# Setup guide — running locally + Instagram (Meta App Review)

## 1. Local run (5 minutes)

```bash
# Backend
cd backend
bash ../scripts/setup_backend.sh
cp .env.example .env
# Set SECRET_KEY and FERNET_KEY in .env (generate with the commands in README.md)
.venv/bin/uvicorn app.main:app --port 8000 --host 127.0.0.1

# Frontend (second terminal)
cd frontend
npm install
npm run dev   # http://localhost:3000
```

Register an account in the UI (or `POST /api/auth/register`), upload a
video, watch the job progress, and open the generated clips. A sample
video is included: `sample/sample_podcast_en.mp4` (English, 250 s) and
`sample/sample_podcast_hi.mp4` (Hindi, 157 s).

## 2. Instagram publishing — what works now, and what needs Meta

**What works now (no Meta app needed):**
- `GET /api/instagram/connect` returns the Meta OAuth URL and explains
  what is missing.
- The publish flow is fully implemented and approval-gated:
  `POST /api/publish` requires `approved=true` (otherwise 403).
- Without a connected account, an approved publish returns
  `status: simulated-pending` with the message “no Instagram token
  connected — publish queued, not published”. It is never presented
  as a real publish.
- Scheduled publishing (`publish_at`) creates a queued job; the worker
  attempts it at the scheduled time and records the result.

**What needs a real Meta app (production):**

1. Create an app at https://developers.facebook.com/apps → type
   **Business** (or Consumer for testing).
2. Add the **Instagram Graph API** product. You need an Instagram
   **Professional** account (Business or Creator) linked to a Facebook Page.
3. In the app, configure **Facebook Login / Instagram Login** with:
   - Valid OAuth redirect URI: `http://localhost:8000/api/instagram/callback`
     for local dev (use your production domain in prod).
   - Scopes: `instagram_basic`, `instagram_content_publish`,
     `pages_read_engagement` (the connect endpoint already requests these).
4. Set `META_APP_ID` and `META_APP_SECRET` in `backend/.env`. The
   callback exchanges the code for a long-lived token, which is stored
   encrypted (Fernet) in the `InstagramAccount` table.
5. **Meta App Review is required for production use** of
   `instagram_content_publish` (and `instagram_basic` beyond test users).
   In dev mode the app works only for users/roles added as test users in
   the Meta app dashboard — add your own Instagram Professional account
   there first and verify the container → publish flow end to end.
6. Reels publishing is container → publish via the Graph API:
   `POST /{ig-user-id}/media` (media_type=REELS, video_url, caption,
   cover_url) → poll container status → `POST /{ig-user-id}/media_publish`.
   The platform implements exactly this (`backend/app/services/instagram.py`,
   `publishing.py`). Meta requires `video_url` to be **publicly reachable**,
   so for production the rendered clip must be served from public storage
   (S3 + signed/public URL) — a local `backend/storage/` path will be
   rejected by Meta with an error stored on the publish job.
7. Scheduling is implemented in our DB + worker, not by Meta (Meta has no
   native Reels scheduling). If a scheduled publish fails, the job is
   retried once, then marked `failed` with the Meta error — never silent.

## 3. Production checklist

- [ ] Postgres: set `DATABASE_URL=postgresql://…` (SQLAlchemy models are
      Postgres-ready; SQLite is dev-only).
- [ ] Redis + Celery workers instead of the DB-polling thread worker
      (same `Job` interface; see `ARCHITECTURE.md` §3).
- [ ] S3-compatible storage via the `Storage` interface
      (`backend/app/services/storage.py`) + public URLs for Reels.
- [ ] Real `SECRET_KEY`, `FERNET_KEY`, `META_APP_ID`, `META_APP_SECRET`
      in environment — never in git or frontend code.
- [ ] Meta App Review approved for `instagram_basic` +
      `instagram_content_publish`; test users added in dev mode.
- [ ] Whisper model: `base` or larger on a GPU worker for long videos and
      better Hindi accuracy; `tiny` is a CPU/dev default.
- [ ] Uploads: put the API behind a reverse proxy with a real upload
      limit/timeout policy; the app enforces 2 GB / 3 h.
