import os
import shutil
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Job, User, Video
from app.schemas import VideoOut
from app.services.rendering import probe

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/upload", response_model=dict, status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    owns_content: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not owns_content:
        raise HTTPException(status_code=400,
                            detail="owns_content: true is required — only upload content you own or are licensed to use")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    settings.videos_dir.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(file.filename)[1].lower() or ".mp4"
    if ext not in {".mp4", ".mov", ".mkv", ".webm", ".avi"}:
        raise HTTPException(status_code=400, detail=f"Unsupported video type: {ext}")
    fname = f"{uuid.uuid4().hex}{ext}"
    dest = settings.videos_dir / fname
    size = 0
    with open(dest, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.MAX_UPLOAD_BYTES:
                out.close()
                os.remove(dest)
                raise HTTPException(status_code=413, detail="File exceeds 2GB limit")
            out.write(chunk)
    meta = probe(str(dest))
    if meta.get("duration") and meta["duration"] > settings.MAX_VIDEO_DURATION_SECONDS:
        os.remove(dest)
        raise HTTPException(status_code=400, detail="Video exceeds 3h duration limit")
    video = Video(user_id=user.id, filename=file.filename, path=str(dest),
                  duration=meta.get("duration") or None, fps=meta.get("fps") or None,
                  width=meta.get("width") or None, height=meta.get("height") or None,
                  owner_attestation=True)
    db.add(video)
    db.commit()
    db.refresh(video)
    job = Job(video_id=video.id, user_id=user.id, status="queued", progress=0, stage="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"video": VideoOut(id=video.id, filename=video.filename, duration=video.duration,
                              fps=video.fps, width=video.width, height=video.height,
                              detected_language=video.detected_language,
                              owner_attestation=True, created_at=video.created_at).model_dump(),
            "job_id": job.id}


@router.get("", response_model=list[VideoOut])
def list_videos(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    videos = db.query(Video).filter(Video.user_id == user.id).order_by(Video.created_at.desc()).all()
    return [VideoOut(id=v.id, filename=v.filename, duration=v.duration, fps=v.fps,
                     width=v.width, height=v.height, detected_language=v.detected_language,
                     owner_attestation=v.owner_attestation,
                     created_at=v.created_at) for v in videos]


@router.get("/{video_id}", response_model=VideoOut)
def get_video(video_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    v = db.query(Video).filter(Video.id == video_id, Video.user_id == user.id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    return VideoOut(id=v.id, filename=v.filename, duration=v.duration, fps=v.fps,
                    width=v.width, height=v.height, detected_language=v.detected_language,
                     owner_attestation=v.owner_attestation,
                    created_at=v.created_at)
