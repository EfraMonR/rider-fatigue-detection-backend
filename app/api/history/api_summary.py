import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import field_validator, model_validator
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.repositories.session_repository import list_sessions

router = APIRouter()


class HistoryQueryParams(BaseModel):
    page: int = Query(default=1, ge=1)
    limit: int = Query(default=10, ge=1, le=100)
    tags: str | None = Query(default=None, description="Comma-separated list of tags")
    date_from: str | None = Query(default=None)
    date_to: str | None = Query(default=None)

    @field_validator("date_from", "date_to", mode="before")
    @classmethod
    def validate_iso8601(cls, v):
        if v is None:
            return v
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("Must be ISO 8601 format")
        return v

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be before date_to")
        return self


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

    # Deserializar campos JSON almacenados como string
    for item in result["items"]:
        for field in ("weather_snapshot", "weather_impact", "tags"):
            if isinstance(item.get(field), str):
                try:
                    item[field] = json.loads(item[field])
                except (ValueError, TypeError):
                    pass

    return result
