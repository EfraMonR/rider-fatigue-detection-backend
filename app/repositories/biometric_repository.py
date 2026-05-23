import uuid

from cryptography.exceptions import InvalidTag
from sqlalchemy import text

from app.db.database import get_connection
from app.utils.encryption import decrypt_bpm, encrypt_bpm
from app.utils.logging import get_logger

logger = get_logger(__name__)


def save_biometric_series(session_id: str, series: list[dict]) -> None:
    """Cifra cada BPM con AES-256-GCM antes de insertar."""
    with get_connection() as conn:
        for row in series:
            bpm_enc, nonce_b64 = encrypt_bpm(row["bpm"])
            conn.execute(
                text("""
                    INSERT INTO biometric_data_raw
                        (id, session_id, timestamp, bpm_encrypted, iv_encrypted, source)
                    VALUES (:id, :session_id, :timestamp, :bpm_encrypted, :iv_encrypted, 'Manual')
                """),
                {
                    "id": uuid.uuid4().hex,
                    "session_id": session_id,
                    "timestamp": row["timestamp"],
                    "bpm_encrypted": bpm_enc,
                    "iv_encrypted": nonce_b64,
                },
            )
        conn.commit()


def get_biometric_series(session_id: str, user_id: str) -> list[dict]:
    """
    Verifica ownership via JOIN con analysis_sessions.
    Lanza InvalidTag si algún ciphertext fue alterado (AEAD).
    """
    with get_connection() as conn:
        rows = conn.execute(
            text("""
                SELECT b.timestamp, b.bpm_encrypted, b.iv_encrypted
                FROM biometric_data_raw b
                JOIN analysis_sessions s ON b.session_id = s.id
                WHERE b.session_id = :session_id AND s.user_id = :user_id
                ORDER BY b.timestamp
            """),
            {"session_id": session_id, "user_id": user_id},
        ).mappings().all()

    result = []
    for row in rows:
        try:
            bpm = decrypt_bpm(row["bpm_encrypted"], row["iv_encrypted"])
        except InvalidTag:
            logger.error("AEAD tag mismatch for session_id=%s — possible tampering", session_id)
            raise
        result.append({"timestamp": row["timestamp"], "bpm": bpm})

    return result
