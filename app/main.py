from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.db.database import engine
from app.api.health import router as health_router
from app.api.routes import public_router, protected_router
from app.api.error_handlers import register_handlers
from app.models_ai.model_loader import load_model, ModelNotAvailableError
from app.utils.logging import get_logger

logger = get_logger(__name__)


def init_db() -> None:
    schema = Path("app/db/schema.sql").read_text(encoding="utf-8")
    dialect = engine.dialect.name
    if dialect == "sqlite":
        # M-1: SQLite requiere executescript para múltiples sentencias
        raw_conn = engine.raw_connection()
        try:
            raw_conn.executescript(schema)
        finally:
            raw_conn.close()
        # Migración: agregar bpm_mean si el DB ya existía sin esa columna
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE analysis_sessions ADD COLUMN bpm_mean REAL DEFAULT NULL"))
                conn.commit()
            except Exception:
                pass  # columna ya existe
    else:
        # M-1: PostgreSQL y otros dialectos compatibles con SQLAlchemy
        with engine.connect() as conn:
            conn.execute(text(schema))
            conn.commit()
    logger.info("Database schema initialized (dialect=%s)", dialect)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # M-2: cargar modelo al arrancar — fallo es no-fatal pero queda en log
    try:
        load_model()
        logger.info("Model loaded at startup")
    except ModelNotAvailableError:
        logger.warning("Model not available at startup — /analysis endpoints devolverán 503")
    yield


app = FastAPI(title="Seguridad Vial API", lifespan=lifespan)

# ── Routes ───────────────────────────────────────────────────────────────────
app.include_router(health_router)        # GET /health (público)
app.include_router(public_router)        # /auth/register, /auth/login
app.include_router(protected_router)     # /auth/refresh, /auth/logout + resto de fases

# ── Error handlers (RF-009) ──────────────────────────────────────────────────
register_handlers(app)
