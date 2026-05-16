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
