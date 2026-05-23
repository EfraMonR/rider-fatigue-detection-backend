import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.repositories.session_repository import list_sessions

router = APIRouter()


@router.get("/history/summary")
def get_history_summary(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    tags: Annotated[str | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    current_user: dict = Depends(get_current_user),
):
    # Validar fechas ISO 8601
    for field_name, val in [("date_from", date_from), ("date_to", date_to)]:
        if val is not None:
            try:
                datetime.fromisoformat(val.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail={"error_code": "INVALID_DATE_FORMAT", "message": f"{field_name} debe ser ISO 8601."},
                )

    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "INVALID_DATE_RANGE", "message": "date_from debe ser anterior a date_to."},
        )

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    result = list_sessions(
        user_id=current_user["user_id"],
        page=page,
        limit=limit,
        tags=tag_list,
        date_from=date_from,
        date_to=date_to,
    )

    for item in result["items"]:
        # H-3: normalizar confidence_score a int 0–100 (datos antiguos pueden ser float 0–1)
        cs = item.get("confidence_score")
        if cs is not None:
            item["confidence_score"] = int(round(cs * 100)) if cs <= 1.0 else int(round(cs))
        # Deserializar campos JSON almacenados como string
        for field in ("weather_snapshot", "weather_impact", "tags"):
            if isinstance(item.get(field), str):
                try:
                    item[field] = json.loads(item[field])
                except (ValueError, TypeError):
                    pass

    return result
