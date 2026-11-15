from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Clip, InstagramAccount, PublishJob, User
from app.schemas import PublishJobOut, PublishRequest
from app.services.publishing import attempt_publish, build_publish_caption

router = APIRouter(prefix="/api/publish", tags=["publish"])


@router.post("", response_model=PublishJobOut, status_code=201)
def publish(payload: PublishRequest, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    if not payload.approved:
        raise HTTPException(status_code=403,
                            detail="Publish requires approved=true — explicit user approval is mandatory")
    clip = db.query(Clip).filter(Clip.id == payload.clip_id, Clip.user_id == user.id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    if not clip.quality_gate_passed:
        raise HTTPException(status_code=400, detail="Clip failed quality gate — cannot publish")
    if not clip.file_path:
        raise HTTPException(status_code=400, detail="Clip has not been rendered yet")
    # Aliases: instagram_account_id (primary) or account_id; scheduled_at
    # (primary) or publish_at. All four spellings are accepted.
    account_id = payload.instagram_account_id if payload.instagram_account_id is not None else payload.account_id
    sched_raw = payload.scheduled_at if payload.scheduled_at is not None else payload.publish_at
    acct = None
    if account_id:
        acct = db.query(InstagramAccount).filter(
            InstagramAccount.id == account_id,
            InstagramAccount.user_id == user.id).first()
    else:
        acct = db.query(InstagramAccount).filter(InstagramAccount.user_id == user.id).first()
    # Editor override: if the caller passes a caption, it becomes the saved
    # selected caption first — the published caption is always the saved one.
    if payload.caption:
        clip.selected_caption = payload.caption
        db.commit()
    job = PublishJob(clip_id=clip.id, user_id=user.id,
                     instagram_account_id=acct.id if acct else None,
                     approved=True, scheduled_at=sched_raw, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    # Scheduled for the future? Queue it — the worker publishes at time.
    from datetime import datetime, timezone
    sched = sched_raw
    if sched is not None and sched.tzinfo is None:
        sched = sched.replace(tzinfo=timezone.utc)
    if sched and sched > datetime.now(timezone.utc):
        job.status = "queued"
        db.commit()
        return PublishJobOut(id=job.id, clip_id=clip.id, approved=True, status="queued",
                             message=f"Scheduled for {sched.isoformat()} — worker will publish then")
    job = attempt_publish(db, job)
    msg = None
    if job.status == "simulated-pending":
        msg = "no Instagram token connected — publish queued, not published"
    elif job.status == "failed":
        msg = "Instagram publish failed — see error; clip was NOT published"
    return PublishJobOut(id=job.id, clip_id=job.clip_id, approved=True, status=job.status,
                         media_id=job.media_id, permalink=job.permalink, error=job.error,
                         message=msg)


@router.get("", response_model=list[PublishJobOut])
def list_publish(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    jobs = db.query(PublishJob).filter(PublishJob.user_id == user.id).order_by(PublishJob.created_at.desc()).all()
    return [PublishJobOut(id=j.id, clip_id=j.clip_id, approved=j.approved, status=j.status,
                          media_id=j.media_id, permalink=j.permalink, error=j.error) for j in jobs]


@router.get("/{publish_id}", response_model=PublishJobOut)
def get_publish(publish_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    j = db.query(PublishJob).filter(PublishJob.id == publish_id, PublishJob.user_id == user.id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Publish job not found")
    return PublishJobOut(id=j.id, clip_id=j.clip_id, approved=j.approved, status=j.status,
                         media_id=j.media_id, permalink=j.permalink, error=j.error)
