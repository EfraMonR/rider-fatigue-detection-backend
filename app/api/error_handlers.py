"""
Handler global de errores — RF-009.
Mapea excepciones a {error_code, message} sin exponer stack trace al cliente.
"""
import errno
import traceback

import httpx
from cryptography.exceptions import InvalidTag
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.repositories.audit_repository import log_event
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Serializa HTTPException respetando el contrato {error_code, message} — RF-009."""
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": "HTTP_ERROR", "message": str(exc.detail)},
    )


async def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    logger.warning("FileNotFoundError: %s", exc)
    return JSONResponse(
        status_code=400,
        content={"error_code": "FILE_NOT_FOUND", "message": "Archivo no encontrado."},
    )


async def operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    logger.error("DB OperationalError: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"error_code": "DATABASE_BUSY", "message": "Base de datos no disponible. Reintentá en unos segundos."},
    )


async def upstream_timeout_handler(request: Request, exc: httpx.TimeoutException) -> JSONResponse:
    logger.warning("Upstream timeout: %s", type(exc).__name__)
    return JSONResponse(
        status_code=504,
        content={"error_code": "UPSTREAM_TIMEOUT", "message": "El servicio externo no respondió a tiempo."},
    )


async def invalid_tag_handler(request: Request, exc: InvalidTag) -> JSONResponse:
    """AEAD tag mismatch — posible tampering de biométricos."""
    logger.error("AEAD InvalidTag detected — possible data tampering on %s %s", request.method, request.url.path)
    log_event(
        user_id=None,
        event_type="model_failure",
        model_status="Error",
        error_message="DATA_INTEGRITY_ERROR: AEAD tag mismatch",
    )
    return JSONResponse(
        status_code=500,
        content={"error_code": "DATA_INTEGRITY_ERROR", "message": "Error de integridad en los datos cifrados."},
    )


async def os_error_handler(request: Request, exc: OSError) -> JSONResponse:
    if exc.errno == errno.ENOSPC:
        logger.error("Disk full (ENOSPC)")
        return JSONResponse(
            status_code=507,
            content={"error_code": "STORAGE_FULL", "message": "Sin espacio en disco. Contactá al administrador."},
        )
    # Cualquier otro OSError cae en el handler genérico
    return await generic_exception_handler(request, exc)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Convierte errores de validación Pydantic a formato {error_code, message}."""
    first_error = exc.errors()[0] if exc.errors() else {}
    field = " → ".join(str(loc) for loc in first_error.get("loc", []))
    msg = first_error.get("msg", "Datos inválidos.")
    return JSONResponse(
        status_code=422,
        content={"error_code": "VALIDATION_ERROR", "message": f"{field}: {msg}" if field else msg},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: stack trace solo a logs, nunca al cliente."""
    logger.error(
        "Unhandled %s on %s %s\n%s",
        type(exc).__name__,
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"error_code": "INTERNAL_ERROR", "message": "Error interno del servidor."},
    )


def register_handlers(app) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(FileNotFoundError, file_not_found_handler)
    app.add_exception_handler(OperationalError, operational_error_handler)
    app.add_exception_handler(httpx.TimeoutException, upstream_timeout_handler)
    app.add_exception_handler(InvalidTag, invalid_tag_handler)
    app.add_exception_handler(OSError, os_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
