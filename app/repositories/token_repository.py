from sqlalchemy import text
from app.db.database import get_connection


def save_refresh_token(user_id: str, token_hash: str, expires_at: str) -> None:
    with get_connection() as conn:
        conn.execute(
            text("""
                INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
                VALUES (:user_id, :token_hash, :expires_at)
            """),
            {"user_id": user_id, "token_hash": token_hash, "expires_at": expires_at},
        )
        conn.commit()


def get_refresh_token(token_hash: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT * FROM refresh_tokens WHERE token_hash = :token_hash"),
            {"token_hash": token_hash},
        ).mappings().first()
        return dict(row) if row else None


def revoke_refresh_token(token_hash: str) -> None:
    with get_connection() as conn:
        conn.execute(
            text("UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = :token_hash"),
            {"token_hash": token_hash},
        )
        conn.commit()


def revoke_all_user_tokens(user_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            text("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        conn.commit()
