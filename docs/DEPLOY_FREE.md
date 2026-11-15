# Free Test Deployment — ViralClip AI (temporary test only)

> **This is a temporary test deployment. Do NOT upload private videos.**
> Free hosting is NOT persistent: uploaded videos and generated clips can be
> lost on restart. Heavy video processing is NOT production-ready on free
> hosting — long videos will be slow and may fail on 512 MB free instances.

## ⚠️ Tunnel result — 2026-11-15: NO public link could be obtained from this VM

All three free, no-account tunnel routes were tried from this VM and all
failed because of the VM's egress proxy — **not** because of the app:

- **Cloudflare quick tunnel (`cloudflared`)**: `api.trycloudflare.com`
  returns `Your request was blocked.` through this VM's egress proxy, and
  `cloudflared tunnel --url …` fails with
  `tls: first record does not look like a TLS handshake`. Deterministic,
  retried twice. Cloudflare's own site loads fine — only the tunnel API is
  blocked.
- **localtunnel (`npx localtunnel --port 3000`)**: process starts but never
  prints a URL (stuck >2 min on the tunnel handshake). Killed.
- **SSH reverse tunnels (`localhost.run`)**: HTTPS site loads, but SSH is
  reset by the egress proxy (`Connection reset by … port 3128`).

**There is no public HTTPS link yet. Do not invent one.** To get one, use
Option B below — it needs the user's own Vercel + Render + GitHub accounts
(no card for the free tiers). That path is fully prepared in this repo
(`render.yaml`, `frontend/vercel.json`, Dockerfiles, env-based CORS).

## Verified locally on this VM (2026-11-15, single-URL mode)

- `tsc --noEmit` exit 0; `npm run build` exit 0, 15 routes.
- Backend `GET /health` → `{"status":"ok"}`; frontend `:3000/upload` → 200.
- Next.js rewrite proxy verified: `GET :3000/api/clips` (no token) → 401
  from FastAPI through the proxy.
- **Real end-to-end run as a test user through the single URL:**
  register → 119-char JWT → upload `sample_podcast_en.mp4` (250.6 s) →
  job 6: 15% transcribing → 45% scenes → 65–75% rendering → **completed
  100 in ~50 s** → 3 clips (scores 76.5 / 75.5 / 71.1).
- Clip download through the proxy: `GET :3000/api/clips/9/file` → 200,
  `video/mp4`, 658,367 bytes, ffprobe 720×1280 H.264+AAC, 25.9 s.
  Cover: 200, JPEG 1080×1920.
- **Mobile 390×844 screenshots** (headless Chrome): see
  `docs/mobile-test/upload-390.png`, `home-390.png`, `clips-390.png` —
  hamburger visible, no horizontal overflow, upload form fits, honest
  "Missing Authorization header" state when logged out (no mock data).
- **Bug found and fixed during this test:** the frontend upload never sent
  `owns_content`, so every UI upload failed with 400, and it did not unwrap
  the backend's `{video, job_id}` response (so `video.id` was undefined).
  Fixed in `frontend/src/lib/api.ts` (`ownsContent` option + unwrap) and
  `frontend/src/components/UploadForm.tsx` (passes `ownsContent: attested`),
  rebuilt and re-verified with the job-6 run above.
- Servers were left running locally for inspection only
  (backend :8000, frontend :3000, this VM only — **not** public).

## What is free here

| Piece | Free option | Cost |
|---|---|---|
| Frontend (Next.js) | Vercel Hobby | $0 — 100 GB transfer, 1M requests/mo, personal non-commercial use only. Pro is $20/seat/mo. |
| Backend (FastAPI) | Render Free web service | $0 — 512 MB RAM, 750 instance-hours/mo, spins down after 15 min idle (~50 s cold start). No free background workers, no persistent disk. |
| Database | Render Free Postgres (1 GB) or SQLite file | $0 — free Postgres **expires 30 days after creation**. SQLite is dev-only. |
| Tunnel (this VM) | Cloudflare Tunnel `trycloudflare.com` | $0, no account, no card. Random `https://<name>.trycloudflare.com` URL, lasts only while the tunnel process runs. |

No billing was enabled and no card was entered for any of this.

## Option A — Tunnel test (fastest, no accounts needed)

Use this to open the site on your phone right now. One public HTTPS URL
serves both frontend and backend: Next.js rewrites `/api/*` to FastAPI.

```bash
# 1. Backend (from ~/workspace/viral-clips/backend)
#    Use a fresh test DB + fresh test secrets — never reuse production keys.
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))") \
FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
CORS_ORIGINS=http://localhost:3000 \
DATABASE_URL=sqlite:///./viral_clips_test.db \
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Frontend (from ~/workspace/viral-clips/frontend)
NEXT_PUBLIC_API_URL=relative NEXT_REWRITE_TO_BACKEND=1 \
  BACKEND_INTERNAL_URL=http://127.0.0.1:8000 npm run dev -- -p 3000
# (or `npm run build && npm run start -p 3000` for the production build)

# 3. Tunnel (anywhere on this VM; cloudflared binary in /tmp)
cloudflared tunnel --url http://127.0.0.1:3000
# It prints: https://<random>.trycloudflare.com — open that on your phone.
```

Notes:
- The tunnel URL is random per run and dies when the tunnel stops. There is
  no permanent free URL without an account.
- `NEXT_PUBLIC_API_URL=relative` + `NEXT_REWRITE_TO_BACKEND=1` is what makes
  one URL serve both apps — the browser never talks to the backend directly,
  so there is no CORS problem in this mode.
- If you open the tunnel URL directly against the backend instead, CORS
  needs `CORS_ALLOW_ORIGIN_REGEX=https://.*\.trycloudflare\.com`
  (test-only, never in production).

## Option B — Vercel Hobby + Render Free (stays up, needs accounts)

You need a GitHub + Vercel account and a Render account. No card is needed
for the free tiers, but **you** must connect the accounts — an agent cannot
sign up for you.

```bash
# 1. Push the repo (from ~/workspace/viral-clips)
git init && git add -A && git commit -m "ViralClip AI — Phase 1"
git remote add origin https://github.com/<you>/viral-clips.git
git push -u origin main
# .gitignore already excludes .env, .venv/, node_modules/, storage/*, *.db

# 2. Vercel: import the repo, root directory `frontend`, framework Next.js.
#    Env var: NEXT_PUBLIC_API_URL=https://<your-render-backend>.onrender.com
#    (leave NEXT_REWRITE_TO_BACKEND unset on Vercel)

# 3. Render: New → Web Service → from the repo, or use render.yaml
#    (root `render.yaml` defines a free Docker web service).
#    Env vars (Render generates SECRET_KEY / FERNET_KEY for you):
#      CORS_ORIGINS=https://<your-vercel-app>.vercel.app
#      DATABASE_URL=sqlite:///./viral_clips.db   (temporary; free Postgres
#        expires in 30 days — see below)
#      WHISPER_MODEL=tiny

# 4. Open https://<your-vercel-app>.vercel.app on your phone.
```

Free-tier limits that will bite:
- Render Free spins down after 15 min idle → first request takes ~50 s.
- Render Free has **no persistent disk** → uploads/clips vanish on restart.
- Render Free Postgres expires after 30 days → use it only for the test.
- 512 MB RAM → Whisper `tiny` on a 60-min podcast takes 15–25 min and can
  OOM on long videos. Keep test videos short (<10 min, <500 MB).
- Vercel Hobby is personal, non-commercial use only.

## Environment variables (complete list)

| Variable | Where | Example |
|---|---|---|
| `SECRET_KEY` | Backend | long random string (generate, never commit) |
| `FERNET_KEY` | Backend | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `DATABASE_URL` | Backend | `sqlite:///./viral_clips.db` (dev) / Render Postgres URL (hosted) |
| `CORS_ORIGINS` | Backend | `https://<frontend>.vercel.app` (comma-separated) |
| `WHISPER_MODEL` | Backend | `tiny` (free test) / `base` (better Hindi) |
| `NEXT_PUBLIC_API_URL` | Frontend | `relative` (tunnel/single-URL) or `https://<backend>.onrender.com` (Vercel) |
| `NEXT_REWRITE_TO_BACKEND` | Frontend | `1` only for tunnel/Docker single-URL mode |
| `BACKEND_INTERNAL_URL` | Frontend | `http://127.0.0.1:8000` (tunnel) / `http://backend:8000` (compose) |

## Proper (paid) setup — for later, not this test

One Docker host (VPS ~$6–12/mo, or Render Standard $25/mo 1 CPU/2 GB)
+ paid Postgres ($6/mo) + persistent disk ($0.25/GB/mo), via
`docker-compose.yml` in this repo. Total ~$12–25/mo. Instagram publishing
additionally needs a Meta app + App Review (see `docs/SETUP.md`).

## Mobile checklist (what was fixed for this test)

- Hamburger drawer sidebar on <lg screens, static sidebar on desktop.
- `viewport` metadata, no horizontal overflow, ≥44 px touch targets.
- Upload: native Android file picker, XHR progress, <500 MB recommendation.
- `<video>` previews use `playsInline`, `preload="metadata"`, controls,
  and a Download link to `/api/clips/{id}/file`.
- Background processing is server-side (DB-polling worker) — it continues
  even if the mobile browser is minimised; the job page polls progress.
- Instagram publishing stays approval-gated (`approved=true` required).
