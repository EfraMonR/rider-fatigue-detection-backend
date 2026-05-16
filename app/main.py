from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import engine
from app.api.health import router as health_router
from app.api.routes import public_router, protected_router
from app.api.error_handlers import register_handlers
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

# ── Routes ───────────────────────────────────────────────────────────────────
app.include_router(health_router)        # GET /health (público)
app.include_router(public_router)        # /auth/register, /auth/login
app.include_router(protected_router)     # /auth/refresh, /auth/logout + resto de fases

# ── Error handlers (RF-009) ──────────────────────────────────────────────────
register_handlers(app)
