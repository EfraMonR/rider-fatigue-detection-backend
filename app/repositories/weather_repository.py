import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.db.database import get_connection


def _coords_key(lat: float, lon: float) -> str:
    return f"{round(lat, 2)},{round(lon, 2)}"


def get_cached_weather(lat: float, lon: float) -> dict | None:
    key = _coords_key(lat, lon)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with get_connection() as conn:
        # Limpieza on-read: borrar registros expirados antes de consultar
        conn.execute(
            text("DELETE FROM weather_cache WHERE expires_at <= :now"),
            {"now": now},
        )
        conn.commit()

        row = conn.execute(
            text("SELECT weather_data_json FROM weather_cache WHERE coordinates_key = :key"),
            {"key": key},
        ).mappings().first()

    return json.loads(row["weather_data_json"]) if row else None


def save_weather(lat: float, lon: float, data: dict, ttl_minutes: int = 15) -> None:
    key = _coords_key(lat, lon)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    with get_connection() as conn:
        conn.execute(
            text("""
                INSERT INTO weather_cache (coordinates_key, weather_data_json, expires_at)
                VALUES (:key, :data, :expires_at)
                ON CONFLICT(coordinates_key) DO UPDATE
                SET weather_data_json = excluded.weather_data_json,
                    expires_at = excluded.expires_at
            """),
            {"key": key, "data": json.dumps(data), "expires_at": expires_at},
        )
        conn.commit()
