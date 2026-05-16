from fastapi import APIRouter, Cookie, Response

from app.repositories import token_repository
from app.services import auth_service
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/auth/logout")
def logout(response: Response, refresh_token: str | None = Cookie(default=None)):
    if refresh_token:
        token_hash = auth_service.hash_refresh_token(refresh_token)
        token_repository.revoke_refresh_token(token_hash)

    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        secure=True,
        samesite="strict",
        path="/auth",
        max_age=0,
    )

    logger.info("Logout completed")

    return {"message": "Sesión cerrada correctamente."}
