# Get your public link from your phone — walkthrough (free test only)

Prepared 2026-11-15 ~17:05 IST, after the tunnel attempt was blocked.
This is a draft checklist, not a deployment. Nothing here was deployed,
no account was created, no billing was enabled.

## Where things stand (verified 2026-11-15 ~11:32 UTC / 17:02 IST)

- Mobile fixes are done and tested at 390×844; backend `/health` is ok and
  frontend `/upload` returns 200 — but both run on this VM only
  (backend :8000, frontend :3000). **There is still no public HTTPS link.**
- The three no-account tunnel routes all failed because of this VM's egress
  proxy, not the app: Cloudflare quick tunnel blocked, localtunnel never
  printed a URL, localhost.run SSH reset. See `docs/DEPLOY_FREE.md`.
- The repo is ready for the account-based route: `render.yaml`,
  `frontend/vercel.json`, `backend/Dockerfile`, `frontend/Dockerfile`,
  env-based CORS. The Termux ZIP is also ready:
  `~/workspace/your_files/viral-clips-termux.zip` (3.2 MB, 126 files).

## Path 1 — Public link (needs your accounts, no card for free tiers)

Do this in this order. The one detail `docs/DEPLOY_FREE.md` does not spell
out: `render.yaml` ships with a placeholder CORS origin
(`https://viral-clips-frontend.vercel.app`). Deploy Vercel first, then put
your real Vercel URL into Render's `CORS_ORIGINS` and redeploy Render.

1. **GitHub** — create a free account if you do not have one, then create an
   empty repo called `viral-clips`. Getting the code onto GitHub is the
   hardest step from a phone alone: it needs a `git push` from a computer,
   or uploading the project files through github.com in a desktop browser.
   `.gitignore` already excludes `.env`, `.venv/`, `node_modules/`,
   `storage/*` and `*.db`, so no secrets go up.
2. **Vercel (free Hobby, $0)** — sign in with GitHub, Import the repo, set
   Root Directory to `frontend`, framework Next.js. Add env var:
   `NEXT_PUBLIC_API_URL=https://<your-render-backend>.onrender.com`
   (you will fill the Render URL in after step 3 — deploy once, then come
   back and set it). Note your app URL, e.g.
   `https://viral-clips-xyz.vercel.app`.
3. **Render (free, $0)** — sign in, New → Web Service → from the same repo
   (or use the `render.yaml` blueprint). It is a free Docker web service,
   `plan: free`, health check `/health`. Env vars:
   - `SECRET_KEY` and `FERNET_KEY` — Render generates these for you.
   - `DATABASE_URL=sqlite:///./viral_clips.db` (temporary test only).
   - `WHISPER_MODEL=tiny`
   - `CORS_ORIGINS=https://<your-real-vercel-app>.vercel.app` — your URL
     from step 2, not the placeholder in `render.yaml`.
   Then redeploy Render so CORS picks up the real frontend URL.
4. **Back in Vercel** — set `NEXT_PUBLIC_API_URL` to your real Render URL
   (`https://<your-backend>.onrender.com`) and redeploy.
5. **Open `https://<your-vercel-app>.vercel.app` on your phone**, register,
   upload a short test video (under 10 min, under 500 MB).

Free-tier limits that will bite (do not ignore): Render Free spins down
after 15 min idle (~50 s cold start), has no persistent disk (uploads and
clips vanish on restart/redeploy), free Postgres expires after 30 days,
and 512 MB RAM can fail on long videos. Temporary test only — do not
upload private videos. Heavy processing is not production-ready here.

## Path 2 — Termux on your phone (no accounts, no public link)

Use this if you want to try a real video today without GitHub/Vercel/Render.
You already have the ZIP from the 11:18 IST message. Unzip it in Termux,
copy `.env.example` to `.env` and set your own `SECRET_KEY` / `FERNET_KEY`,
then start backend `:8000` and frontend `:3000` as in the README. This runs
on your phone only — it is not a shareable public link.

## What I still need from you

Pick one: (a) "walk me through the public-link deploy" and tell me whether
you have GitHub / Vercel / Render accounts already, or (b) "I'll try the
Termux ZIP first". I cannot create those accounts or sign in as you.

## Phase 2 — deliberately not decided here

The Phase 2 plan (`docs/PHASE2_PLAN.md`) is still on disk, undecided. It
is not the next step until you have tried a real video through one of the
paths above — that try-first test is what Phase 2A (topic-boundary
enforcement, Whisper `base` for Hindi, semantic hashtags) is waiting on.
