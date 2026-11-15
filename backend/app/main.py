"""FastAPI entrypoint."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, auth, clips, instagram, jobs, publish, videos
from app.core.config import settings
from app.core.database import init_db
from app.workers.worker import start_worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Viral Clipping Automation Platform", version="0.1.0")

# CORS is env-based (settings.CORS_ORIGINS, comma-separated). Default is
# local dev only; the deployed frontend origin must be set via env — see
# backend/.env.example and docs/DEPLOY_FREE.md. No public URL is hardcoded.
_cors_kwargs = {
    "allow_origins": settings.cors_origins,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.cors_origin_regex:
    # Temporary free-tunnel test only. Never enable in production.
    _cors_kwargs["allow_origin_regex"] = settings.cors_origin_regex
app.add_middleware(CORSMiddleware, **_cors_kwargs)

app.include_router(auth.router)
app.include_router(videos.router)
app.include_router(jobs.router)
app.include_router(clips.router)
app.include_router(instagram.router)
app.include_router(publish.router)
app.include_router(analytics.router)


@app.on_event("startup")
def on_startup():
    init_db()
    start_worker()
    logger.info("Backend started; job worker polling DB job table")


@app.get("/health")
def health():
    return {"status": "ok", "service": "viral-clips-backend"}
