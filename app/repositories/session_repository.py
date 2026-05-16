import json
import uuid

from sqlalchemy import text

from app.db.database import get_connection
from app.utils.logging import get_logger

logger = get_logger(__name__)


def create_session(user_id: str, result_dict: dict) -> str:
    """Inserta la sesión solo cuando el análisis fue exitoso. Siempre processing_status='completed'."""
    session_id = uuid.uuid4().hex
    with get_connection() as conn:
        conn.execute(
            text("""
                INSERT INTO analysis_sessions
                    (id, user_id, verdict, stress_level, traffic_light,
                     weather_snapshot, weather_impact, risk_score, confidence_score,
                     tags, processing_status)
                VALUES
                    (:id, :user_id, :verdict, :stress_level, :traffic_light,
                     :weather_snapshot, :weather_impact, :risk_score, :confidence_score,
                     :tags, 'completed')
            """),
            {
                "id": session_id,
                "user_id": user_id,
                "verdict": result_dict["verdict"],
                "stress_level": result_dict["stress_level"],
                "traffic_light": result_dict["traffic_light"],
                "weather_snapshot": json.dumps(result_dict.get("weather_snapshot", {})),
                "weather_impact": json.dumps(result_dict["weather_impact"]) if result_dict.get("weather_impact") else None,
                "risk_score": result_dict.get("risk_score"),
                "confidence_score": result_dict.get("confidence_score"),
                "tags": json.dumps(result_dict.get("tags", [])),
            },
        )
        # Incrementar session_count del usuario
        conn.execute(
            text("UPDATE users SET session_count = session_count + 1 WHERE id = :user_id"),
            {"user_id": user_id},
        )
        conn.commit()
    return session_id


def get_session_by_id(session_id: str, user_id: str) -> dict | None:
    """404 uniforme si no existe o pertenece a otro usuario (anti-IDOR)."""
    with get_connection() as conn:
        row = conn.execute(
            text("""
                SELECT * FROM analysis_sessions
                WHERE id = :session_id AND user_id = :user_id
            """),
            {"session_id": session_id, "user_id": user_id},
        ).mappings().first()
        return dict(row) if row else None


# Columnas permitidas en filtros dinámicos — whitelist anti-SQLi
_FILTERABLE_DATE_COLS = frozenset({"timestamp"})


def list_sessions(
    user_id: str,
    page: int = 1,
    limit: int = 10,
    tags: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    conditions = ["user_id = :user_id"]
    params: dict = {"user_id": user_id}

    if date_from:
        conditions.append("timestamp >= :date_from")
        params["date_from"] = date_from

    if date_to:
        conditions.append("timestamp <= :date_to")
        params["date_to"] = date_to

    if tags:
        for i, tag in enumerate(tags):
            key = f"tag_{i}"
            # json_each es seguro: la columna 'tags' es hardcodeada, el valor va parametrizado
            conditions.append(
                f"EXISTS (SELECT 1 FROM json_each(tags) WHERE value = :{key})"
            )
            params[key] = tag

    where_clause = " AND ".join(conditions)
    params["limit"] = limit
    params["offset"] = (page - 1) * limit

    with get_connection() as conn:
        total = conn.execute(
            text(f"SELECT COUNT(*) FROM analysis_sessions WHERE {where_clause}"),
            params,
        ).scalar()

        rows = conn.execute(
            text(f"""
                SELECT id, timestamp, verdict, stress_level, traffic_light,
                       weather_snapshot, weather_impact, risk_score, confidence_score, tags
                FROM analysis_sessions
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        ).mappings().all()

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


def get_session_detail(session_id: str, user_id: str, include_raw: bool = False) -> dict | None:
    row = get_session_by_id(session_id, user_id)
    if row is None:
        return None

    result = dict(row)

    if include_raw:
        # import tardío para evitar ciclo: session_repo → biometric_repo → encryption
        from app.repositories.biometric_repository import get_biometric_series
        result["raw_data"] = get_biometric_series(session_id, user_id)
    else:
        result["raw_data"] = None

    return result


def delete_session(session_id: str, user_id: str) -> bool:
    """Retorna True si borró, False si no existía o era de otro usuario (anti-IDOR)."""
    with get_connection() as conn:
        result = conn.execute(
            text("""
                DELETE FROM analysis_sessions
                WHERE id = :session_id AND user_id = :user_id
            """),
            {"session_id": session_id, "user_id": user_id},
        )
        conn.commit()
    return result.rowcount > 0
