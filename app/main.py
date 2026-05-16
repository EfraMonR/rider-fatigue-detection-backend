from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.db.database import engine
from app.api.health import router as health_router
from app.utils.logging import get_logger

logger = get_logger(__name__)


def init_db() -> None:
    schema = Path("app/db/schema.sql").read_text(encoding="utf-8")
    raw_conn = engine.raw_connection()
    try:
        raw_conn.executescript(schema)
    finally:
        raw_conn.close()
    logger.info("Database schema initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Seguridad Vial API", lifespan=lifespan)

# ── Public routes ────────────────────────────────────────────────────────────
app.include_router(health_router)


# ── Global error handler (full implementation: task 5.16) ────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s %s — %s", request.method, request.url.path, type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"error_code": "INTERNAL_ERROR", "message": "Error interno del servidor."},
    )
