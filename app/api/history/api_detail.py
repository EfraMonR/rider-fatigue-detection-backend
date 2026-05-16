import json

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated

from app.api.dependencies import get_current_user
from app.repositories.session_repository import get_session_detail

router = APIRouter()


@router.get("/history/{session_id}")
def get_history_detail(
    session_id: str,
    raw_data: Annotated[bool, Query()] = False,
    current_user: dict = Depends(get_current_user),
):
    result = get_session_detail(
        session_id=session_id,
        user_id=current_user["user_id"],
        include_raw=raw_data,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "SESSION_NOT_FOUND", "message": "Sesión no encontrada."},
        )

    for field in ("weather_snapshot", "weather_impact", "tags"):
        if isinstance(result.get(field), str):
            try:
                result[field] = json.loads(result[field])
            except (ValueError, TypeError):
                pass

    return result
