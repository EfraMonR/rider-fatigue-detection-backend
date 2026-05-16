from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.api.dependencies import get_current_user
from app.repositories import contact_repository

router = APIRouter()


class ContactIn(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None


class ContactUpdateIn(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None


@router.get("/user/contacts")
def list_contacts(current_user: dict = Depends(get_current_user)):
    return contact_repository.get_contacts_by_user(current_user["user_id"])


@router.post("/user/contacts", status_code=201)
def create_contact(body: ContactIn, current_user: dict = Depends(get_current_user)):
    return contact_repository.create_contact(
        user_id=current_user["user_id"],
        name=body.name,
        email=body.email,
        phone=body.phone,
    )


@router.put("/user/contacts/{contact_id}")
def update_contact(
    contact_id: str,
    body: ContactUpdateIn,
    current_user: dict = Depends(get_current_user),
):
    updated = contact_repository.update_contact(
        contact_id=contact_id,
        user_id=current_user["user_id"],
        data=body.model_dump(exclude_none=True),
    )
    if not updated:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "CONTACT_NOT_FOUND", "message": "Contacto no encontrado."},
        )
    return updated


@router.delete("/user/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: str, current_user: dict = Depends(get_current_user)):
    deleted = contact_repository.delete_contact(contact_id, current_user["user_id"])
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "CONTACT_NOT_FOUND", "message": "Contacto no encontrado."},
        )
