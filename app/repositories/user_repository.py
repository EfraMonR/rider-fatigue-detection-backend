import math

from sqlalchemy import text

from app.db.database import get_connection


def get_user_by_email(email: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": email},
        ).mappings().first()
        return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE id = :id"),
            {"id": user_id},
        ).mappings().first()
        return dict(row) if row else None


def create_user(id: str, name: str, email: str, password_hash: str) -> dict:
    with get_connection() as conn:
        conn.execute(
            text("""
                INSERT INTO users (id, name, email, password_hash)
                VALUES (:id, :name, :email, :password_hash)
            """),
            {"id": id, "name": name, "email": email, "password_hash": password_hash},
        )
        conn.commit()
    return get_user_by_id(id)


def update_last_login(user_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            text("""
                UPDATE users
                SET last_login = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE id = :id
            """),
            {"id": user_id},
        )
        conn.commit()


# Campos del perfil expuestos al cliente — excluye password_hash y encryption_key
_PROFILE_FIELDS = (
    "id", "name", "email", "baseline_bpm", "profile_status",
    "session_count", "last_stability_check", "last_login", "created_at",
)


def get_profile(user_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE id = :id"),
            {"id": user_id},
        ).mappings().first()
    if row is None:
        return None
    return {k: row[k] for k in _PROFILE_FIELDS if k in row}


def update_baseline_bpm(user_id: str, bpm: int) -> None:
    with get_connection() as conn:
        conn.execute(
            text("UPDATE users SET baseline_bpm = :bpm WHERE id = :id"),
            {"bpm": bpm, "id": user_id},
        )
        conn.commit()


def recalculate_profile_status(user_id: str) -> str:
    """
    Regla (RF-007): new → calibrating en la 1ª sesión; calibrating → stable
    cuando session_count >= 5 Y stddev(bpm_mean) < 10% del promedio en los últimos 7 días.
    Actualiza la fila y devuelve el nuevo status.
    """
    with get_connection() as conn:
        user_row = conn.execute(
            text("SELECT session_count, profile_status FROM users WHERE id = :id"),
            {"id": user_id},
        ).mappings().first()
        if user_row is None:
            return "new"

        count = user_row["session_count"]
        current = user_row["profile_status"]

        if count == 0:
            new_status = "new"
        elif count < 5:
            new_status = "calibrating"
        else:
            # SQLite no tiene STDDEV; calculamos en Python sobre bpm_mean (últimos 7 días)
            bpm_means = conn.execute(
                text("""
                    SELECT bpm_mean FROM analysis_sessions
                    WHERE user_id = :uid
                      AND bpm_mean IS NOT NULL
                      AND timestamp >= datetime('now', '-7 days')
                """),
                {"uid": user_id},
            ).scalars().all()

            if len(bpm_means) >= 5:
                mean = sum(bpm_means) / len(bpm_means)
                variance = sum((b - mean) ** 2 for b in bpm_means) / len(bpm_means)
                stddev = math.sqrt(variance)
                # Criterio: desviación < 10% del BPM promedio
                threshold = mean * 0.10
                new_status = "stable" if stddev < threshold else "calibrating"
            else:
                new_status = "calibrating"

        if new_status != current:
            conn.execute(
                text("""
                    UPDATE users
                    SET profile_status = :status,
                        last_stability_check = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    WHERE id = :id
                """),
                {"status": new_status, "id": user_id},
            )
            conn.commit()

    return new_status
