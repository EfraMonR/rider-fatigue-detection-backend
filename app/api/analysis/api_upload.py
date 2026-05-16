from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile

from app.api.dependencies import get_current_user
from app.config import settings
from app.models_ai.model_loader import ModelNotAvailableError
from app.services import analysis_service, etl_service
from app.services.etl_service import ETLError
from app.utils.validators import validate_csv_filename

router = APIRouter()

_ALLOWED_CONTENT_TYPES = {"text/csv", "application/json"}
_MAX_ROWS = 5000


@router.post("/analysis/upload-file")
async def upload_file(
    request: Request,
    file: UploadFile,
    lat: float | None = None,
    lon: float | None = None,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    # 1) Validar Content-Length antes de leer en memoria
    content_length = request.headers.get("content-length")
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if content_length and int(content_length) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail={"error_code": "FILE_TOO_LARGE",
                    "message": "Archivo excede el límite de procesamiento online. Procesar localmente en la app."},
        )

    # 2) Validar content-type
    content_type = (file.content_type or "").split(";")[0].strip()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail={"error_code": "UNSUPPORTED_MEDIA_TYPE",
                    "message": "Solo se aceptan archivos CSV o JSON."},
        )

    # 3) Validar nombre de archivo
    filename = file.filename or ""
    if not validate_csv_filename(filename):
        raise HTTPException(
            status_code=400,
            detail={"error_code": "INVALID_FILENAME",
                    "message": "Nombre de archivo inválido."},
        )

    # 4) Leer body
    file_bytes = await file.read()
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail={"error_code": "FILE_TOO_LARGE",
                    "message": "Archivo excede el límite de procesamiento online. Procesar localmente en la app."},
        )

    # 5) ETL
    try:
        etl_result = etl_service.run_etl(file_bytes, filename)
    except ETLError as exc:
        detail = {"error_code": exc.error_code, "message": exc.message}
        detail.update(exc.extra)
        raise HTTPException(status_code=400, detail=detail)

    series = etl_result["series"]

    # 6) Post-ETL: límite de filas
    if len(series) > _MAX_ROWS:
        raise HTTPException(
            status_code=413,
            detail={"error_code": "FILE_TOO_LARGE",
                    "message": "Archivo excede el límite de procesamiento online. Procesar localmente en la app."},
        )

    # 7) Análisis síncrono — sin BackgroundTasks
    try:
        result = analysis_service.process(user_id=user_id, series=series, lat=lat, lon=lon)
    except ModelNotAvailableError:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "MODEL_NOT_AVAILABLE",
                    "message": "El servicio de análisis no está disponible temporalmente. Intentá nuevamente en unos minutos."},
        )

    result["rejected_rows"] = etl_result["rejected_rows"]
    return result
