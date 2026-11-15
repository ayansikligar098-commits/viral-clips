"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str


class VideoOut(BaseModel):
    id: int
    filename: str
    duration: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    detected_language: Optional[str] = None
    owner_attestation: bool = False
    created_at: Optional[datetime] = None


class JobOut(BaseModel):
    id: int
    video_id: int
    status: str
    progress: int
    stage: str
    error: Optional[str] = None
    retries: int = 0


class ClipOut(BaseModel):
    id: int
    video_id: int
    start_time: float
    end_time: float
    score: float
    score_breakdown: dict = {}
    quality_gate_passed: bool = False
    quality_gate_failures: List[str] = []
    context_preserved: bool = False
    context_reason: Optional[str] = None
    title: Optional[str] = None
    title_variations: List[str] = []
    caption: Optional[str] = None
    caption_variations: List[str] = []
    hashtags: List[str] = []
    hooks: List[str] = []
    hook_variations: List[str] = []  # alias of hooks — 3+ opening-hook variations
    selected_caption: Optional[str] = None
    selected_hook: Optional[str] = None
    cta: Optional[str] = None
    detected_language: Optional[str] = None
    file_path: Optional[str] = None
    cover_path: Optional[str] = None
    caption_style: str = "Bold Yellow"
    edit_style: str = "Podcast"
    style: str = "Podcast"  # alias of edit_style, for clients that send/read `style`
    status: str = "ready"


class ClipPatch(BaseModel):
    """Editor update — pre-filled auto text, editable before publishing.
    Only supplied fields change. Accepts both `edit_style` and the `style`
    alias the frontend sends."""
    title: Optional[str] = None
    title_variations: Optional[List[str]] = None
    caption: Optional[str] = None
    caption_variations: Optional[List[str]] = None
    hashtags: Optional[List[str]] = None
    hooks: Optional[List[str]] = None
    hook_variations: Optional[List[str]] = None
    selected_caption: Optional[str] = None
    selected_hook: Optional[str] = None
    cta: Optional[str] = None
    caption_style: Optional[str] = None
    edit_style: Optional[str] = None
    style: Optional[str] = None  # alias of edit_style


class RenderRequest(BaseModel):
    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    # Aliases the frontend also sends — accepted identically.
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    caption_style: Optional[str] = None  # Bold Yellow | White Minimal | Neon | Hormozi-style
    edit_style: Optional[str] = None  # Podcast | Gaming | Cinematic | Hormozi-inspired | Minimal Captions
    style: Optional[str] = None  # alias of edit_style


class PublishRequest(BaseModel):
    clip_id: int
    approved: bool = False
    instagram_account_id: Optional[int] = None
    account_id: Optional[int] = None  # alias of instagram_account_id
    scheduled_at: Optional[datetime] = None
    publish_at: Optional[datetime] = None  # alias of scheduled_at
    caption: Optional[str] = None


class YoutubeUrlRequest(BaseModel):
    """Paste-a-YouTube-link request. owns_content must be true, exactly
    like file upload — only content the user owns or is licensed to use."""
    youtube_url: str
    owns_content: bool = False
    title: Optional[str] = None


class PublishJobOut(BaseModel):
    id: int
    clip_id: int
    approved: bool
    status: str
    media_id: Optional[str] = None
    permalink: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None


class AnalyticsOut(BaseModel):
    id: int
    clip_id: Optional[int] = None
    publish_job_id: Optional[int] = None
    views: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    source: str = "graph_api"


class InstagramConnectOut(BaseModel):
    oauth_url: str
    note: str
