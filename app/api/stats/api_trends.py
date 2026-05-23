from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.repositories.session_repository import get_trends

router = APIRouter()


@router.get("/stats/trends")
def stats_trends(
    period: Annotated[str, Query()] = "week",
    current_user: dict = Depends(get_current_user),
):
    if period not in ("week", "month"):
        raise HTTPException(
            status_code=422,
            detail={"error_code": "INVALID_PERIOD", "message": "period debe ser 'week' o 'month'."},
        )

    result = get_trends(user_id=current_user["user_id"], period=period)

    if not result["points"]:
        result["message"] = "Sin datos para el período seleccionado."

    return result
