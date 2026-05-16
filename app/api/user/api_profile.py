from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user
from app.repositories.user_repository import get_profile

router = APIRouter()


@router.get("/user/profile")
def get_user_profile(current_user: dict = Depends(get_current_user)):
    profile = get_profile(user_id=current_user["user_id"])
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "USER_NOT_FOUND", "message": "Usuario no encontrado."},
        )
    return profile
