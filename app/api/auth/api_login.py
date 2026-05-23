from fastapi import APIRouter, HTTPException, Response

from app.api.auth.schemas import LoginIn
from app.repositories import audit_repository, user_repository, token_repository
from app.services import auth_service
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

_REFRESH_COOKIE_MAX_AGE = 7 * 24 * 3600
_INVALID_CREDENTIALS = HTTPException(
    status_code=401,
    detail={"error_code": "INVALID_CREDENTIALS", "message": "Email o contraseña incorrectos."},
)


@router.post("/auth/login")
def login(body: LoginIn, response: Response):
    user = user_repository.get_user_by_email(body.email)

    # Mensaje uniforme — no diferencia email inexistente vs password incorrecta (anti-enumeración)
    if not user or not auth_service.verify_password(body.password, user["password_hash"]):
        # user_id puede ser None si el email no existe
        audit_repository.log_event(
            user_id=user["id"] if user else None,
            event_type="login",
            error_message="INVALID_CREDENTIALS",
        )
        raise _INVALID_CREDENTIALS

    user_id = user["id"]
    token_repository.revoke_all_user_tokens(user_id)
    user_repository.update_last_login(user_id)

    access_token = auth_service.create_access_token(user_id)
    token_raw, token_hash = auth_service.create_refresh_token(user_id)
    expires_at = auth_service.refresh_token_expires_at()
    token_repository.save_refresh_token(user_id, token_hash, expires_at)

    response.set_cookie(
        key="refresh_token",
        value=token_raw,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/auth",
        max_age=_REFRESH_COOKIE_MAX_AGE,
    )

    audit_repository.log_event(user_id=user_id, event_type="login", model_status="Success")
    logger.info("Login successful user_id=%s", user_id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "profile_status": user["profile_status"],
        "session_count": user["session_count"],
    }
