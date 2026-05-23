from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, HTTPException, Response

from app.repositories import token_repository
from app.services import auth_service
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

_REFRESH_COOKIE_MAX_AGE = 7 * 24 * 3600
_TOKEN_INVALID = HTTPException(
    status_code=401,
    detail={"error_code": "REFRESH_TOKEN_INVALID", "message": "Sesión expirada. Por favor, volvé a ingresar."},
)


@router.post("/auth/refresh")
def refresh(response: Response, refresh_token: str | None = Cookie(default=None)):
    if not refresh_token:
        raise _TOKEN_INVALID

    token_hash = auth_service.hash_refresh_token(refresh_token)
    record = token_repository.get_refresh_token(token_hash)

    if not record or record["revoked"]:
        raise _TOKEN_INVALID

    expires_at = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        raise _TOKEN_INVALID

    user_id = record["user_id"]
    token_repository.revoke_refresh_token(token_hash)

    access_token = auth_service.create_access_token(user_id)
    new_token_raw, new_token_hash = auth_service.create_refresh_token(user_id)
    new_expires_at = auth_service.refresh_token_expires_at()
    token_repository.save_refresh_token(user_id, new_token_hash, new_expires_at)

    response.set_cookie(
        key="refresh_token",
        value=new_token_raw,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/auth",
        max_age=_REFRESH_COOKIE_MAX_AGE,
    )

    logger.info("Token rotated user_id=%s", user_id)

    return {"access_token": access_token, "token_type": "bearer"}
