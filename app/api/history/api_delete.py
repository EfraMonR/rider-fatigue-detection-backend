from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user
from app.repositories.session_repository import delete_session

router = APIRouter()


@router.delete("/history/{session_id}", status_code=200)
def delete_history_entry(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    deleted = delete_session(session_id=session_id, user_id=current_user["user_id"])

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "SESSION_NOT_FOUND", "message": "Sesión no encontrada."},
        )

    return {"message": "Sesión eliminada correctamente."}
