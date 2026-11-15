"""Instagram via official Meta Graph API only (container -> publish).

No real Meta token = no publishing. Functions raise / return clear errors
when no token is connected. Token exchange + encrypted storage via Fernet.
Requires Meta App Review for production; dev mode works with test users.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.security import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)
SCOPES = ["instagram_basic", "instagram_content_publish", "pages_read_engagement"]


def build_oauth_url(state: str = "") -> str:
    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": settings.META_REDIRECT_URI,
        "scope": ",".join(SCOPES),
        "response_type": "code",
    }
    if state:
        params["state"] = state
    return f"https://www.facebook.com/{settings.GRAPH_API_VERSION}/dialog/oauth?{urlencode(params)}"


def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """Short-lived token exchange. Requires real META_APP_ID/SECRET."""
    if not settings.META_APP_ID or not settings.META_APP_SECRET:
        raise RuntimeError("META_APP_ID / META_APP_SECRET not configured — cannot exchange OAuth code")
    url = f"https://graph.facebook.com/{settings.GRAPH_API_VERSION}/oauth/access_token"
    resp = httpx.get(url, params={
        "client_id": settings.META_APP_ID,
        "client_secret": settings.META_APP_SECRET,
        "redirect_uri": settings.META_REDIRECT_URI,
        "code": code,
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()


def encrypt_access_token(token: str) -> str:
    return encrypt_token(token)


def decrypt_access_token(encrypted: str) -> str:
    return decrypt_token(encrypted)


def create_container(ig_user_id: str, access_token: str, video_url: str,
                     caption: str) -> str:
    """Create a Reels media container. Returns container id."""
    url = f"https://graph.facebook.com/{settings.GRAPH_API_VERSION}/{ig_user_id}/media"
    resp = httpx.post(url, data={
        "media_type": "REELS", "video_url": video_url, "caption": caption,
        "access_token": access_token,
    }, timeout=60)
    data = resp.json()
    if resp.status_code >= 400 or "id" not in data:
        raise RuntimeError(f"Graph API container failed: {data}")
    return data["id"]


def poll_container_status(container_id: str, access_token: str) -> str:
    url = f"https://graph.facebook.com/{settings.GRAPH_API_VERSION}/{container_id}"
    resp = httpx.get(url, params={"fields": "status_code", "access_token": access_token}, timeout=30)
    data = resp.json()
    return data.get("status_code", "UNKNOWN")


def publish_container(ig_user_id: str, access_token: str, container_id: str) -> Dict[str, Any]:
    url = f"https://graph.facebook.com/{settings.GRAPH_API_VERSION}/{ig_user_id}/media_publish"
    resp = httpx.post(url, data={"creation_id": container_id, "access_token": access_token}, timeout=60)
    data = resp.json()
    if resp.status_code >= 400 or "id" not in data:
        raise RuntimeError(f"Graph API publish failed: {data}")
    return data  # {"id": media_id}


def get_media_permalink(media_id: str, access_token: str) -> Optional[str]:
    url = f"https://graph.facebook.com/{settings.GRAPH_API_VERSION}/{media_id}"
    resp = httpx.get(url, params={"fields": "permalink", "access_token": access_token}, timeout=30)
    if resp.status_code == 200:
        return resp.json().get("permalink")
    return None
