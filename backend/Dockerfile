# Viral Clips backend — FastAPI + FFmpeg + faster-whisper (CPU-only).
# Free-test image. No secrets are baked in: SECRET_KEY / FERNET_KEY /
# DATABASE_URL / CORS_ORIGINS must come from the host environment.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Storage is a mounted volume on the host (see docker-compose.yml).
# On Render Free there is NO persistent disk — files are lost on restart.
RUN mkdir -p storage/videos storage/clips storage/covers

EXPOSE 8000
# Render / Fly set $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
