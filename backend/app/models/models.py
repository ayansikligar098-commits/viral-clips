"""SQLAlchemy models — same schema for SQLite (dev) and Postgres (prod)."""
import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    videos = relationship("Video", back_populates="user")
    instagram_accounts = relationship("InstagramAccount", back_populates="user")


class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(512), nullable=False)
    path = Column(String(1024), nullable=False)
    duration = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    detected_language = Column(String(16), nullable=True)  # en | hi | hinglish | ...
    owner_attestation = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    user = relationship("User", back_populates="videos")
    jobs = relationship("Job", back_populates="video")
    clips = relationship("Clip", back_populates="video")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(32), default="queued", nullable=False)  # queued/processing/completed/failed
    progress = Column(Integer, default=0, nullable=False)
    stage = Column(String(128), default="queued", nullable=False)
    error = Column(Text, nullable=True)
    retries = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    video = relationship("Video", back_populates="jobs")


class Clip(Base):
    __tablename__ = "clips"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    score = Column(Float, default=0.0, nullable=False)
    score_breakdown = Column(Text, default="{}", nullable=False)  # JSON {factor: {score, reason}}
    quality_gate_passed = Column(Boolean, default=False, nullable=False)
    quality_gate_failures = Column(Text, default="[]", nullable=False)  # JSON list[str]
    context_preserved = Column(Boolean, default=False, nullable=False)
    context_reason = Column(Text, nullable=True)
    title = Column(String(255), nullable=True)
    title_variations = Column(Text, default="[]", nullable=False)  # JSON list[str] (3)
    caption = Column(Text, nullable=True)
    caption_variations = Column(Text, default="[]", nullable=False)  # JSON list[str] (3)
    hashtags = Column(Text, default="[]", nullable=False)  # JSON list[str]
    hooks = Column(Text, default="[]", nullable=False)  # JSON list[str] (3+)
    selected_caption = Column(Text, nullable=True)  # editor pick, default = caption_variations[0]
    selected_hook = Column(String(512), nullable=True)  # editor pick, default = hooks[0]
    cta = Column(String(255), nullable=True)
    detected_language = Column(String(16), nullable=True)  # en | hi | hinglish
    file_path = Column(String(1024), nullable=True)
    cover_path = Column(String(1024), nullable=True)
    caption_style = Column(String(64), default="Bold", nullable=False)
    edit_style = Column(String(64), default="Podcast", nullable=False)
    status = Column(String(32), default="ready", nullable=False)  # ready/rendering/failed
    created_at = Column(DateTime, default=_utcnow)
    video = relationship("Video", back_populates="clips")

    # JSON helpers
    def breakdown(self):
        try:
            return json.loads(self.score_breakdown or "{}")
        except Exception:
            return {}

    def gate_failures(self):
        try:
            return json.loads(self.quality_gate_failures or "[]")
        except Exception:
            return []

    def hashtag_list(self):
        try:
            return json.loads(self.hashtags or "[]")
        except Exception:
            return []

    def hook_list(self):
        try:
            return json.loads(self.hooks or "[]")
        except Exception:
            return []

    def hook_variation_list(self):
        """Alias of hook_list — the response field is `hook_variations`."""
        return self.hook_list()

    def title_variation_list(self):
        try:
            return json.loads(self.title_variations or "[]")
        except Exception:
            return []

    def caption_variation_list(self):
        try:
            return json.loads(self.caption_variations or "[]")
        except Exception:
            return []


class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ig_user_id = Column(String(128), nullable=False)
    username = Column(String(128), nullable=True)
    encrypted_access_token = Column(Text, nullable=False)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    user = relationship("User", back_populates="instagram_accounts")


class PublishJob(Base):
    __tablename__ = "publish_jobs"
    id = Column(Integer, primary_key=True, index=True)
    clip_id = Column(Integer, ForeignKey("clips.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=True)
    approved = Column(Boolean, default=False, nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="queued", nullable=False)  # queued/published/failed/simulated-pending
    media_id = Column(String(128), nullable=True)
    permalink = Column(String(512), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class Analytics(Base):
    __tablename__ = "analytics"
    id = Column(Integer, primary_key=True, index=True)
    clip_id = Column(Integer, ForeignKey("clips.id"), nullable=True)
    publish_job_id = Column(Integer, ForeignKey("publish_jobs.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    views = Column(Integer, default=0, nullable=False)
    reach = Column(Integer, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    shares = Column(Integer, default=0, nullable=False)
    saves = Column(Integer, default=0, nullable=False)
    source = Column(String(64), default="graph_api", nullable=False)
    recorded_at = Column(DateTime, default=_utcnow)
