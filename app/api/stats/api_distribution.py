from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.repositories.session_repository import get_distribution

router = APIRouter()


@router.get("/stats/distribution")
def stats_distribution(current_user: dict = Depends(get_current_user)):
    result = get_distribution(user_id=current_user["user_id"])

    if result["total"] < 2:
        result["message"] = "Se necesitan al menos 2 sesiones para calcular la distribución."

    return result
