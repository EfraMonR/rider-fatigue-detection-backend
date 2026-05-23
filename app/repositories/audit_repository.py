import json
import uuid

from sqlalchemy import text

from app.db.database import get_connection
from app.utils.logging import get_logger

logger = get_logger(__name__)


def log_event(
    user_id: str | None,
    event_type: str,
    model_status: str | None = None,
    error_message: str | None = None,
    details: dict | None = None,
) -> None:
    """
    Registra un evento en audit_logs.
    Nunca propaga excepciones: un fallo de auditoría no debe cortar el flujo principal.
    """
    try:
        with get_connection() as conn:
            conn.execute(
                text("""
                    INSERT INTO audit_logs
                        (id, user_id, event_type, model_status, error_message, details)
                    VALUES
                        (:id, :user_id, :event_type, :model_status, :error_message, :details)
                """),
                {
                    "id": uuid.uuid4().hex,
                    "user_id": user_id,
                    "event_type": event_type,
                    "model_status": model_status,
                    "error_message": error_message,
                    "details": json.dumps(details or {}),
                },
            )
            conn.commit()
    except Exception as exc:
        # Loguear pero nunca relanzar — la auditoría es best-effort
        logger.error("audit_repository.log_event failed: %s", exc)
