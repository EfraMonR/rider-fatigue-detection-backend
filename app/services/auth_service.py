import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

_ALGORITHM = "HS256"
_SPECIAL_CHAR_RE = re.compile(r"[^a-zA-Z0-9]")


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def validate_password_strength(plain: str) -> bool:
    return len(plain) >= 8 and bool(_SPECIAL_CHAR_RE.search(plain))


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=_ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Returns (token_raw, sha256_hash). Only the hash is persisted."""
    token_raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
    return token_raw, token_hash


def refresh_token_expires_at() -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    return expire.strftime("%Y-%m-%dT%H:%M:%SZ")


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[_ALGORITHM])
    except JWTError:
        return None


def hash_refresh_token(token_raw: str) -> str:
    return hashlib.sha256(token_raw.encode()).hexdigest()
