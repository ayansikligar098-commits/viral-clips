"""Shared publish logic — used by the API and by the worker for scheduled
publishing. The caption used is ALWAYS the saved (edited or auto) one:
clip.selected_caption (editor pick) -> clip.caption (auto) — plus the
clip's hashtags appended automatically. No manual caption writing needed.

Honest limitation: Meta requires a publicly reachable video_url, so a
local file path cannot be published from this VM. When no token is
connected the job stays 'simulated-pending'; when a token exists but the
video is not publicly hosted, the Graph API error is stored on the job.
"""
import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import decrypt_token
from app.models.models import Clip, InstagramAccount, PublishJob
from app.services.instagram import (create_container, get_media_permalink,
                                    poll_container_status, publish_container)

logger = logging.getLogger(__name__)


def build_publish_caption(clip: Clip, override: Optional[str] = None) -> str:
    """Saved caption (edited pick wins) + hashtags, automatically."""
    text = (override or clip.selected_caption or clip.caption or "").strip()
    tags = clip.hashtag_list()
    if tags:
        text = f"{text}\n\n{' '.join(tags)}" if text else " ".join(tags)
    return text


def attempt_publish(db: Session, job: PublishJob) -> PublishJob:
    """Attempt a real Graph API publish for one PublishJob. Mutates job
    (status/media_id/permalink/error) and commits. Returns the job."""
    clip = db.query(Clip).filter(Clip.id == job.clip_id).first()
    if not clip or not clip.file_path:
        job.status, job.error = "failed", "Clip not rendered yet"
        db.commit()
        return job
    acct = None
    if job.instagram_account_id:
        acct = db.query(InstagramAccount).filter(
            InstagramAccount.id == job.instagram_account_id).first()
    if not acct:
        acct = db.query(InstagramAccount).filter(
            InstagramAccount.user_id == job.user_id).first()
    if not acct:
        job.status = "simulated-pending"
        job.error = "no Instagram token connected — publish queued, not published"
        db.commit()
        return job
    try:
        token = decrypt_token(acct.encrypted_access_token)
        caption = build_publish_caption(clip)
        container_id = create_container(acct.ig_user_id, token, clip.file_path, caption)
        status = "UNKNOWN"
        for _ in range(10):
            status = poll_container_status(container_id, token)
            if status in ("FINISHED", "ERROR"):
                break
            time.sleep(5)
        if status == "ERROR":
            raise RuntimeError("Meta container processing failed")
        result = publish_container(acct.ig_user_id, token, container_id)
        job.media_id = result.get("id")
        job.permalink = get_media_permalink(job.media_id, token)
        job.status = "published"
        job.error = None
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = str(exc)
        logger.warning("Publish job %s failed: %s", job.id, exc)
    db.commit()
    return job
