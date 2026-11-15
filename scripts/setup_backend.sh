#!/usr/bin/env bash
# Create venv at backend/.venv and install requirements.
set -euo pipefail
cd "$(dirname "$0")/../backend"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
mkdir -p storage/videos storage/clips storage/covers
touch storage/videos/.gitkeep storage/clips/.gitkeep storage/covers/.gitkeep
if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example — edit SECRET_KEY / FERNET_KEY before production use."; fi
echo "Backend venv ready. Run: .venv/bin/uvicorn app.main:app --port 8000"
