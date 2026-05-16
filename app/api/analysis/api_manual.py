from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from app.api.dependencies import get_current_user
from app.models_ai.model_loader import ModelNotAvailableError
from app.services import analysis_service
from app.utils.validators import validate_bpm, validate_timestamp

router = APIRouter()

_MAX_ROWS = 5000


class BpmPoint(BaseModel):
    timestamp: str
    bpm: float

    @field_validator("bpm")
    @classmethod
    def bpm_in_range(cls, v: float) -> float:
        if not validate_bpm(v):
            raise ValueError("BPM fuera del rango fisiológico [30, 220]")
        return v

    @field_validator("timestamp")
    @classmethod
    def ts_parseable(cls, v: str) -> str:
        if not validate_timestamp(v):
            raise ValueError("Timestamp no parseable como ISO 8601")
        return v


class ManualInputIn(BaseModel):
    series: list[BpmPoint]
    lat: float | None = None
    lon: float | None = None


@router.post("/analysis/manual-input")
async def manual_input(
    body: ManualInputIn,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    if len(body.series) > _MAX_ROWS:
        raise HTTPException(
            status_code=413,
            detail={"error_code": "FILE_TOO_LARGE",
                    "message": "Archivo excede el límite de procesamiento online. Procesar localmente en la app."},
        )

    if not body.series:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "NO_VALID_ROWS",
                    "message": "El payload no contiene datos de ritmo cardíaco válidos."},
        )

    series = [{"timestamp": p.timestamp, "bpm": p.bpm} for p in body.series]

    try:
        result = await analysis_service.process(user_id=user_id, series=series, lat=body.lat, lon=body.lon)
    except ModelNotAvailableError:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "MODEL_NOT_AVAILABLE",
                    "message": "El servicio de análisis no está disponible temporalmente. Intentá nuevamente en unos minutos."},
        )

    result["rejected_rows"] = []
    return result
