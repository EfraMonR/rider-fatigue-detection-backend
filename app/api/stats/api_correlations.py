from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.repositories.session_repository import get_correlations

router = APIRouter()


@router.get("/stats/correlations")
def stats_correlations(current_user: dict = Depends(get_current_user)):
    return get_correlations(user_id=current_user["user_id"])
