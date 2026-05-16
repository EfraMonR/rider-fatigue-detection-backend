import json

import httpx

from app.config import settings
from app.repositories import audit_repository, contact_repository, session_repository
from app.utils.logging import get_logger

logger = get_logger(__name__)
_audit_available = True


async def send_alert(user_id: str, session_id: str, contact_ids: list[str] | None = None) -> dict:
    """
    Envía alerta por email a los contactos del usuario vía SendGrid.
    Si contact_ids está vacío, notifica a todos los contactos del usuario.
    Devuelve {"sent": [email,...], "failed": [email,...]}.
    """
    session = session_repository.get_session_by_id(session_id, user_id)
    if not session:
        return {"sent": [], "failed": [], "error": "SESSION_NOT_FOUND"}

    if contact_ids:
        contacts = [
            contact_repository.get_contact_by_id(cid, user_id)
            for cid in contact_ids
        ]
        contacts = [c for c in contacts if c is not None]
    else:
        contacts = contact_repository.get_contacts_by_user(user_id)

    if not contacts:
        return {"sent": [], "failed": [], "error": "NO_CONTACTS_FOUND"}

    weather_impact = session.get("weather_impact")
    if weather_impact and isinstance(weather_impact, str):
        try:
            weather_impact = json.loads(weather_impact)
        except Exception:
            weather_impact = None

    sent, failed = [], []
    for contact in contacts:
        try:
            await _send_via_sendgrid(
                to_email=contact["email"],
                to_name=contact["name"],
                session=session,
                weather_impact=weather_impact,
            )
            sent.append(contact["email"])
            logger.info("Alert sent to contact contact_id=%s", contact["id"])
        except Exception as exc:
            failed.append(contact["email"])
            logger.error("Alert failed for contact_id=%s: %s", contact["id"], type(exc).__name__)
            _log_alert_error(user_id, session_id, str(type(exc).__name__))

    if sent:
        _log_alert_success(user_id, session_id)

    return {"sent": sent, "failed": failed}


async def _send_via_sendgrid(
    to_email: str,
    to_name: str,
    session: dict,
    weather_impact: dict | None,
) -> None:
    traffic_light = session.get("traffic_light", "Unknown")
    stress_level = session.get("stress_level", "Unknown")
    verdict = session.get("verdict", "Unknown")
    timestamp = session.get("timestamp", "")

    weather_line = ""
    if weather_impact:
        weather_line = f"\nImpacto climático ({weather_impact.get('severity','')}: {weather_impact.get('message','')})"

    body_text = (
        f"Alerta de Seguridad Vial\n\n"
        f"El conductor ha registrado un nivel de estrés elevado.\n\n"
        f"Estado: {verdict}\n"
        f"Nivel de estrés: {stress_level}\n"
        f"Semáforo: {traffic_light}\n"
        f"Fecha: {timestamp}"
        f"{weather_line}\n\n"
        f"Por favor comuníquese con el conductor."
    )

    payload = {
        "personalizations": [{"to": [{"email": to_email, "name": to_name}]}],
        "from": {"email": settings.SENDGRID_FROM_EMAIL},
        "subject": f"[Seguridad Vial] Alerta: semáforo {traffic_light}",
        "content": [{"type": "text/plain", "value": body_text}],
    }

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        response = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
        )
        response.raise_for_status()


def _log_alert_success(user_id: str, session_id: str) -> None:
    if not _audit_available:
        return
    try:
        audit_repository.log_event(
            user_id=user_id,
            event_type="alert_sent",
            model_status="Success",
            details={"session_id": session_id},
        )
    except Exception:
        pass


def _log_alert_error(user_id: str, session_id: str, error: str) -> None:
    if not _audit_available:
        return
    try:
        audit_repository.log_event(
            user_id=user_id,
            event_type="alert_sent",
            model_status="Error",
            error_message=error,
            details={"session_id": session_id},
        )
    except Exception:
        pass
