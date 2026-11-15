"""Env-based settings. Postgres-ready via DATABASE_URL; SQLite is the dev default."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-change-me")
    FERNET_KEY: str = os.getenv("FERNET_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'viral_clips.db'}")
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", str(BASE_DIR / "storage"))
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "tiny")
    MAX_CLIPS_PER_VIDEO: int = _int("MAX_CLIPS_PER_VIDEO", 5)
    DEFAULT_CLIPS_PER_VIDEO: int = _int("DEFAULT_CLIPS_PER_VIDEO", 3)
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = _int("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
    MAX_UPLOAD_BYTES: int = _int("MAX_UPLOAD_BYTES", 2 * 1024 * 1024 * 1024)
    MAX_VIDEO_DURATION_SECONDS: int = _int("MAX_VIDEO_DURATION_SECONDS", 3 * 3600)
    # YouTube link downloads: free-test guard, max video length (seconds).
    YOUTUBE_MAX_DURATION_SECONDS: int = _int("YOUTUBE_MAX_DURATION_SECONDS", 900)
    META_APP_ID: str = os.getenv("META_APP_ID", "")
    META_APP_SECRET: str = os.getenv("META_APP_SECRET", "")
    META_REDIRECT_URI: str = os.getenv("META_REDIRECT_URI", "http://localhost:8000/api/instagram/callback")
    GRAPH_API_VERSION: str = os.getenv("GRAPH_API_VERSION", "v21.0")
    # CORS — env-based. Comma-separated origins, e.g.
    # CORS_ORIGINS=http://localhost:3000,https://viral-clips.vercel.app
    # Default is local dev only. NEVER put secrets here; origins are public
    # hostnames, not credentials. For the temporary free tunnel test only,
    # CORS_ALLOW_ORIGIN_REGEX can allow https://*.trycloudflare.com (see
    # docs/DEPLOY_FREE.md). Do not enable the regex in production.
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )
    CORS_ALLOW_ORIGIN_REGEX: str = os.getenv("CORS_ALLOW_ORIGIN_REGEX", "")

    @property
    def cors_origins(self) -> list:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def cors_origin_regex(self) -> str:
        return self.CORS_ALLOW_ORIGIN_REGEX.strip()

    @property
    def storage_dir(self) -> Path:
        p = Path(self.STORAGE_DIR)
        # Resolve relative STORAGE_DIR (e.g. "./storage" from .env) against
        # backend/ so stored file paths are absolute regardless of cwd.
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    @property
    def videos_dir(self) -> Path:
        return self.storage_dir / "videos"

    @property
    def clips_dir(self) -> Path:
        return self.storage_dir / "clips"

    @property
    def covers_dir(self) -> Path:
        return self.storage_dir / "covers"


settings = Settings()
