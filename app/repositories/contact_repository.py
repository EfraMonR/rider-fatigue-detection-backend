import uuid

from sqlalchemy import text

from app.db.database import get_connection


def get_contacts_by_user(user_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            text("SELECT * FROM trusted_contacts WHERE user_id = :user_id ORDER BY created_at"),
            {"user_id": user_id},
        ).mappings().all()
        return [dict(r) for r in rows]


def get_contact_by_id(contact_id: str, user_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT * FROM trusted_contacts WHERE id = :id AND user_id = :user_id"),
            {"id": contact_id, "user_id": user_id},
        ).mappings().first()
        return dict(row) if row else None


def create_contact(user_id: str, name: str, email: str, phone: str | None) -> dict:
    contact_id = uuid.uuid4().hex
    with get_connection() as conn:
        conn.execute(
            text("""
                INSERT INTO trusted_contacts (id, user_id, name, email, phone)
                VALUES (:id, :user_id, :name, :email, :phone)
            """),
            {"id": contact_id, "user_id": user_id, "name": name, "email": email, "phone": phone},
        )
        conn.commit()
    return get_contact_by_id(contact_id, user_id)


def update_contact(contact_id: str, user_id: str, data: dict) -> dict | None:
    existing = get_contact_by_id(contact_id, user_id)
    if not existing:
        return None

    name = data.get("name", existing["name"])
    email = data.get("email", existing["email"])
    phone = data.get("phone", existing["phone"])

    with get_connection() as conn:
        conn.execute(
            text("""
                UPDATE trusted_contacts
                SET name = :name, email = :email, phone = :phone
                WHERE id = :id AND user_id = :user_id
            """),
            {"name": name, "email": email, "phone": phone, "id": contact_id, "user_id": user_id},
        )
        conn.commit()
    return get_contact_by_id(contact_id, user_id)


def delete_contact(contact_id: str, user_id: str) -> bool:
    with get_connection() as conn:
        result = conn.execute(
            text("DELETE FROM trusted_contacts WHERE id = :id AND user_id = :user_id"),
            {"id": contact_id, "user_id": user_id},
        )
        conn.commit()
        return result.rowcount > 0
