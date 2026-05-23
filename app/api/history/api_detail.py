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

    # H-3: normalizar confidence_score a int 0–100 (datos antiguos pueden ser float 0–1)
    cs = result.get("confidence_score")
    if cs is not None:
        result["confidence_score"] = int(round(cs * 100)) if cs <= 1.0 else int(round(cs))

    for field in ("weather_snapshot", "weather_impact", "tags"):
        if isinstance(result.get(field), str):
            try:
                result[field] = json.loads(result[field])
            except (ValueError, TypeError):
                pass

    return result
