from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.repositories import contact_repository, session_repository
from app.services import alerts_service

router = APIRouter()


class AlertSendIn(BaseModel):
    session_id: str
    contact_ids: list[str] = []


@router.post("/alerts/send")
async def send_alert(
    body: AlertSendIn,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    # Validar que la sesión pertenece al usuario
    session = session_repository.get_session_by_id(body.session_id, user_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "SESSION_NOT_FOUND", "message": "Sesión no encontrada."},
        )

    # Validar que cada contact_id pertenece al usuario (anti-IDOR)
    for cid in body.contact_ids:
        if not contact_repository.get_contact_by_id(cid, user_id):
            raise HTTPException(
                status_code=404,
                detail={"error_code": "CONTACT_NOT_FOUND", "message": "Contacto no encontrado."},
            )

    result = await alerts_service.send_alert(
        user_id=user_id,
        session_id=body.session_id,
        contact_ids=body.contact_ids or None,
    )

    if result.get("error") == "NO_CONTACTS_FOUND":
        raise HTTPException(
            status_code=400,
            detail={"error_code": "NO_CONTACTS_FOUND", "message": "El usuario no tiene contactos registrados."},
        )

    if not result["sent"] and result["failed"]:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "ALERT_SERVICE_UNAVAILABLE", "message": "No se pudo enviar la alerta. Intente nuevamente."},
        )

    return {"sent": result["sent"], "failed": result["failed"]}
