import json
import uuid

from sqlalchemy import text

from app.db.database import get_connection


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
