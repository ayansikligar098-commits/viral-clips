"""Analytics — DB-only aggregation. No mock data: empty list + message when none."""
from sqlalchemy.orm import Session

from app.models.models import Analytics


def list_analytics(db: Session, user_id: int):
    return (db.query(Analytics).filter(Analytics.user_id == user_id)
            .order_by(Analytics.recorded_at.desc()).all())


def summary(db: Session, user_id: int) -> dict:
    rows = list_analytics(db, user_id)
    if not rows:
        return {"total_clips": 0, "views": 0, "reach": 0, "likes": 0, "comments": 0,
                "shares": 0, "saves": 0, "message": "No analytics data yet — publish a clip first."}
    return {"total_clips": len(rows),
            "views": sum(r.views for r in rows),
            "reach": sum(r.reach for r in rows),
            "likes": sum(r.likes for r in rows),
            "comments": sum(r.comments for r in rows),
            "shares": sum(r.shares for r in rows),
            "saves": sum(r.saves for r in rows),
            "message": None}
