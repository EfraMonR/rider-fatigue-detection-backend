"""
Tags del usuario almacenadas en users.threshold_config (JSON).
Estructura: {"tags": [{"id": "<uuid_hex>", "name": "<str>"}]}
No hay tabla separada en el DDL actual (decisión MVP para no requerir migración).
"""
import json
import uuid

from sqlalchemy import text

from app.db.database import get_connection


def _load_config(conn, user_id: str) -> dict:
    row = conn.execute(
        text("SELECT threshold_config FROM users WHERE id = :id"),
        {"id": user_id},
    ).mappings().first()
    if row is None:
        return {}
    try:
        return json.loads(row["threshold_config"] or "{}")
    except (ValueError, TypeError):
        return {}


def _save_config(conn, user_id: str, config: dict) -> None:
    conn.execute(
        text("UPDATE users SET threshold_config = :cfg WHERE id = :id"),
        {"cfg": json.dumps(config), "id": user_id},
    )


def get_tags(user_id: str) -> list[dict]:
    with get_connection() as conn:
        config = _load_config(conn, user_id)
    return config.get("tags", [])


def create_tag(user_id: str, name: str) -> dict | None:
    """Retorna None si el nombre ya existe (case-insensitive)."""
    with get_connection() as conn:
        config = _load_config(conn, user_id)
        tags = config.get("tags", [])

        if any(t["name"].lower() == name.lower() for t in tags):
            return None  # duplicado

        new_tag = {"id": uuid.uuid4().hex, "name": name}
        tags.append(new_tag)
        config["tags"] = tags
        _save_config(conn, user_id, config)
        conn.commit()

    return new_tag


def delete_tag(tag_id: str, user_id: str) -> bool:
    """Retorna False si el tag no existe o pertenece a otro usuario (anti-IDOR)."""
    with get_connection() as conn:
        config = _load_config(conn, user_id)
        tags = config.get("tags", [])
        original_len = len(tags)

        tags = [t for t in tags if t["id"] != tag_id]
        if len(tags) == original_len:
            return False  # no encontrado

        config["tags"] = tags
        _save_config(conn, user_id, config)
        conn.commit()

    return True
