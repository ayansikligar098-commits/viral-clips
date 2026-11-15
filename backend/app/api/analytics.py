from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User
from app.schemas import AnalyticsOut
from app.services.analytics import list_analytics, summary

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
def get_analytics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = list_analytics(db, user.id)
    if not rows:
        return {"rows": [], "message": "No analytics data yet — publish a clip first. No mock data is shown."}
    return {"rows": [AnalyticsOut(id=r.id, clip_id=r.clip_id, publish_job_id=r.publish_job_id,
                                  views=r.views, reach=r.reach, likes=r.likes, comments=r.comments,
                                  shares=r.shares, saves=r.saves, source=r.source) for r in rows],
            "message": None}


@router.get("/summary")
def get_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return summary(db, user.id)
