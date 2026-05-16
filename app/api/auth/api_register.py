import uuid

from fastapi import APIRouter, HTTPException, Response

from app.api.auth.schemas import RegisterIn
from app.repositories import user_repository, token_repository
from app.services import auth_service
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

_REFRESH_COOKIE_MAX_AGE = 7 * 24 * 3600  # 7 días en segundos


@router.post("/auth/register", status_code=201)
def register(body: RegisterIn, response: Response):
    if not auth_service.validate_password_strength(body.password):
        raise HTTPException(
            status_code=400,
            detail={"error_code": "WEAK_PASSWORD", "message": "La contraseña debe tener al menos 8 caracteres e incluir un carácter especial."},
        )

    if user_repository.get_user_by_email(body.email):
        raise HTTPException(
            status_code=409,
            detail={"error_code": "EMAIL_ALREADY_EXISTS", "message": "Este email ya está registrado."},
        )

    user_id = uuid.uuid4().hex
    password_hash = auth_service.hash_password(body.password)
    user = user_repository.create_user(
        id=user_id,
        name=body.name,
        email=body.email,
        password_hash=password_hash,
    )

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

    logger.info("User registered successfully user_id=%s", user_id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "profile_status": user["profile_status"],
        "session_count": user["session_count"],
    }
