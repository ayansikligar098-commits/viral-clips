# YouTube Link Feature

Paste a YouTube video link on the Upload page; the backend downloads the
video and runs the **existing** AI analysis → clip pipeline on it, exactly
as for a file upload (same quality gate: max 5 clips, default 3, same
subtitles, scores, covers, metadata).

## Status (2026-11-15, local implementation — NOT pushed to GitHub yet)

- Backend endpoint, frontend tab, and validation are implemented and tested
  locally (see Test results below).
- The user's test video (podcast) is **69.5 minutes** long, so the endpoint
  correctly rejects it under the 15-minute free-test guard. A trimmed
  first-15-minutes test was attempted, but a full media download of that
  video is blocked in this VM (see "Known limits").

## Backend

### Endpoint: `POST /api/videos/from-url` (auth required)

Request JSON:

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
  "owns_content": true,
  "title": "optional override"
}
```

Response (201, same shape as file upload):

```json
{ "video": { "id": 1, "filename": "…", "duration": 634.5, "...": "..." },
  "job_id": 1 }
```

The created `Job` is picked up by the existing DB-polling worker, so the
pipeline (probe → Whisper transcribe → scenes/silence → context-aware
windows → scoring + quality gate → render → metadata → cover) runs
unchanged. The analysis page polls `JobProgress` for that job, exactly as
for uploads.

### Validation

| Case | Result |
| --- | --- |
| No auth token | 401 |
| `owns_content` false/missing | 400 — attestation required (same wording as upload) |
| Not a URL / wrong scheme | 400 |
| Non-YouTube URL (e.g. example.com) | 400 |
| youtube.com without `v=` / bad video id | 400 |
| Video unavailable / private / restricted | 400 |
| YouTube / network blocks the download | 502 with a clear message |
| Video longer than 15 min (free-test guard) | 400 — "…69 minutes long — the free test only accepts YouTube videos up to 15 minutes." |

Accepted URLs: `youtube.com/watch?v=<id>`, `youtu.be/<id>`,
`youtube.com/shorts/<id>` (www / m / music subdomains allowed; `?si=`
tracking params are stripped by canonicalisation).

### Download — `backend/app/services/youtube.py`

- Uses `yt-dlp` (pinned in `backend/requirements.txt`; no Dockerfile
  change needed — yt-dlp is pure Python via pip, ffmpeg was already in
  the image).
- Format: combined mp4 `best[height<=720][ext=mp4]` (android client serves
  itag 18/22, no merge needed, no PO token needed).
- Player client: **android** (`extractor_args youtube.player_client=
  android`). The web client is bot-checked ("Sign in to confirm you're
  not a bot") from shared/datacentre IPs and YouTube now forces SABR
  streaming on it, so its https DASH formats have no usable URL.
- `http_chunk_size = 1 MB`: the egress proxy cuts long transfers; small
  Range chunks + retries get through where one big GET stalls.
- `retries = fragment_retries = 30` (raised from 10 after repeated
  mid-chunk proxy cuts; untested end-to-end — see below).
- Proxy/CA (dev VM only): when `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE`
  is set, yt-dlp uses `compat_opts = {'no-certifi'}` (system cert store,
  verification stays ON) and the proxy from `https_proxy`/`HTTPS_PROXY`.
  On Render those env vars are absent, so defaults apply unchanged.
- Free-test guard: `YOUTUBE_MAX_DURATION_SECONDS` (default 900 = 15 min,
  env-overridable). Checked from metadata *before* downloading, and again
  from ffprobe after download.
- Files land in `storage/videos/<uuid>.mp4`, the same directory the upload
  flow uses. No secrets, no cookies, no playlists.

## Frontend

- `frontend/src/components/UploadForm.tsx`: mobile-friendly tab switch
  **File Upload | YouTube Link** (44px touch targets, same card).
- YouTube tab: URL input (`type=url`), optional title, the same
  ownership checkbox (required), "Fetch video & create clips" button.
  While downloading it shows "Downloading from YouTube…"; on success it
  routes to `/analysis/<videoId>` where the existing `JobProgress`
  component polls the job — identical to the file-upload flow.
- `frontend/src/lib/api.ts`: new typed `createVideoFromUrl(youtubeUrl,
  {title, ownsContent})` returning `{video, job_id}`. The old dead
  `uploadVideoByUrl` helper (it called a never-existing `/upload-url`
  endpoint) now delegates to it.
- Upload page copy mentions the YouTube option. File upload is untouched.

## Files changed

- `backend/app/services/youtube.py` (new)
- `backend/app/api/videos.py` (new `POST /from-url`, upload untouched)
- `backend/app/schemas.py` (`YoutubeUrlRequest`)
- `backend/app/core/config.py` (`YOUTUBE_MAX_DURATION_SECONDS`, default 900)
- `backend/requirements.txt` (`yt-dlp==2026.10.26`)
- `frontend/src/components/UploadForm.tsx` (tabs)
- `frontend/src/app/upload/page.tsx` (copy)
- `frontend/src/lib/api.ts` (`createVideoFromUrl`, fixed `uploadVideoByUrl`)

## Test results (local, 2026-11-15)

- Frontend: `npx tsc --noEmit` exit 0; `npm run build` exit 0, 15 routes.
- Backend smoke test: `tests/smoke_test.py` — 27/27 pass.
- Test server on :8001 (throwaway DB/storage): all validation curls above
  returned the expected status + message; no-auth → 401.
- User's test video: `https://youtu.be/VdLKK1EQ92A` — "TJR: Why New
  Traders Keep FAILING, They Need To Understand THIS" (Titans Of Tomorrow),
  **4170 s = 69.5 min**. Endpoint correctly returns 400 (15-min guard).
- End-to-end download test — FINAL RESULT (2026-11-15): **not completed
  in this VM.** Big Buck Bunny (`aqz-KE-bpKQ`, 634 s, 27.2 MiB) via
  `POST /api/videos/from-url`:
  - Attempt 1: 502 after ~20 s — a 1 MB chunk failed 10 retries (~11 MB
    downloaded, partial `.part` file left in test storage).
  - Attempt 2: 502 after ~36 s — same chunk failure (~3.5 MB).
  - Attempt 3: curl hit its 600 s client timeout (HTTP 000); the server
    thread kept downloading to 84.8% (24.1/27.2 MiB), then the final
    chunk failed 10 retries → 502. No Video/Job rows were created in any
    attempt (creation happens only after a successful download), so no
    job reached the worker and **no rendered clips from a YouTube
    download were produced in this VM**.
  - Retries were raised 10 → 30 in `youtube.py` after attempt 3, but the
    change was NOT re-tested end-to-end (wrap-up ordered a stop).
  - Counter-evidence the code path can work: one full CLI download of
    the same video DID succeed earlier (28,523,658 bytes, ffprobe
    634.6 s, 640x360 h264+aac) with 1 MB chunks. Later identical CLI
    attempts failed with connection cuts / read timeouts — the egress
    proxy's reliability varies over time and degrades with repeated
    downloads (possible throttling of the shared proxy IP).

## Known limits (honest)

- **This VM cannot reliably download YouTube media right now.** The
  egress proxy cuts long googlevideo transfers; web/iOS/TV player clients
  are bot-checked from the shared proxy IP, and the android client's
  itag 18 URL for the user's podcast serves only the moov header
  (`Content-Length: 1944336`, server ends the stream there; a Range
  beyond it returns HTTP 416). One full 27.2 MiB download (Big Buck Bunny,
  634 s) *did* succeed via CLI with 1 MB chunks, proving the download
  options work when the network cooperates — but repeated attempts in
  this VM then failed with connection cuts / read timeouts, so a
  completed end-to-end job run could not be reproduced on demand here.
- **On Render (no egress proxy) downloads should behave normally** —
  the proxy/CA workarounds are env-gated and inactive there. The first
  real test should be done on the deployed backend, with a video the
  user owns.
- The 15-minute guard is a free-test limit, not a product limit; raise
  `YOUTUBE_MAX_DURATION_SECONDS` (and Render RAM/time) to lift it.
- Only use videos you own or are licensed to use; the endpoint requires
  the ownership attestation, and YouTube may still block some videos
  (bot-check / PO token / age restriction) — those surface as a clear
  400/502, never a silent fake clip.

## Auth fix + re-test (main agent, 2026-11-15, test server :8001)

- Root cause of the live "Missing Authorization header" dashboard error:
  `POST /api/auth/register` returned only the user (no token), so Sign up
  left the user with no JWT; and `GET /api/auth/me` did not exist, so the
  Topbar never showed the signed-in state. Fixed: register now returns a
  JWT, `/me` exists, the dashboard skips protected calls when logged out
  (sign-in prompt instead), clears an expired token on 401, and the
  upload form blocks submit when logged out. Frontend `register()` also
  auto-logs-in if a backend ever returns no token.
- Re-test: register → `access_token` returned; `/me` → the test user;
  no-token `GET /api/videos` → 401 as expected (backend correct, frontend
  no longer triggers it logged-out). `tsc` + `npm run build` pass,
  15 routes; smoke test 27/27.
- Big Buck Bunny via `POST /api/videos/from-url`: 2 more attempts, both
  502 (proxy cut the transfer after ~0.7 MB / ~0.4 MB, 30 retries). The
  retries 10 → 30 change was therefore re-tested end-to-end and still
  fails in this VM — the decisive test must run on Render after push.
- 69-min podcast guard re-verified: `VdLKK1EQ92A` → 400, 15-minute limit.
