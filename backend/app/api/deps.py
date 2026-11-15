"""Shared auth dependency."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer),
                     db: Session = Depends(get_db)) -> User:
    if not creds:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    sub = decode_access_token(creds.credentials)
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == int(sub)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
