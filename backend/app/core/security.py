"""JWT + bcrypt password hashing + Fernet encryption for stored tokens."""
import base64
import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": subject, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def _fernet():
    """Fernet instance, or None if no FERNET_KEY configured.

    Falls back to a key derived from SECRET_KEY so local dev still works;
    production must set a dedicated FERNET_KEY.
    """
    from cryptography.fernet import Fernet

    key = settings.FERNET_KEY.strip() if settings.FERNET_KEY else ""
    if not key:
        digest = hashlib.sha256(f"fernet:{settings.SECRET_KEY}".encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode())


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
