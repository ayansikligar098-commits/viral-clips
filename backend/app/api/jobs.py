from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Job, User
from app.schemas import JobOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut(id=job.id, video_id=job.video_id, status=job.status, progress=job.progress,
                  stage=job.stage, error=job.error, retries=job.retries)
