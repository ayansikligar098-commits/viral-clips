from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import decrypt_token
from app.models.models import InstagramAccount, User
from app.schemas import InstagramConnectOut
from app.services.instagram import build_oauth_url, encrypt_access_token, exchange_code_for_token

router = APIRouter(prefix="/api/instagram", tags=["instagram"])


@router.get("/connect", response_model=InstagramConnectOut)
def connect(user: User = Depends(get_current_user)):
    return InstagramConnectOut(
        oauth_url=build_oauth_url(state=str(user.id)),
        note=("Connect a Professional Instagram account via Meta OAuth. "
              "Production publishing requires Meta App Review for "
              "instagram_basic + instagram_content_publish; dev mode works with "
              "test users added to the Meta app. No token = no publishing."))


@router.get("/callback")
def callback(code: str = Query(None), access_token: str = Query(None),
             ig_user_id: str = Query(None), username: str = Query(None),
             db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Stub: stores an encrypted token when code+token are supplied.

    Real flow: Meta redirects here with ?code=...; we exchange it for a
    long-lived token. For dev/testing, a directly supplied access_token +
    ig_user_id is accepted and stored encrypted."""
    token = access_token
    if code and not token:
        try:
            data = exchange_code_for_token(code)
            token = data.get("access_token")
            ig_user_id = ig_user_id or str(data.get("user_id", ""))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {exc}")
    if not token or not ig_user_id:
        raise HTTPException(status_code=400,
                            detail="No token supplied — provide ?code= (Meta redirect) or ?access_token= + ?ig_user_id=")
    acct = InstagramAccount(user_id=user.id, ig_user_id=str(ig_user_id),
                            username=username, encrypted_access_token=encrypt_access_token(token))
    db.add(acct)
    db.commit()
    db.refresh(acct)
    return {"account_id": acct.id, "ig_user_id": acct.ig_user_id, "username": acct.username,
            "message": "Instagram account connected (token stored encrypted)"}


@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    accts = db.query(InstagramAccount).filter(InstagramAccount.user_id == user.id).all()
    return [{"id": a.id, "ig_user_id": a.ig_user_id, "username": a.username,
             "token_expires_at": a.token_expires_at} for a in accts]


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = db.query(InstagramAccount).filter(InstagramAccount.id == account_id,
                                          InstagramAccount.user_id == user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(a)
    db.commit()
    return {"deleted": account_id}
