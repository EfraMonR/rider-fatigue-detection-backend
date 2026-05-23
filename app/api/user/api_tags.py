from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from app.api.dependencies import get_current_user
from app.repositories.tag_repository import create_tag, delete_tag, get_tags

router = APIRouter()


class TagIn(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre del tag no puede estar vacío.")
        if len(v) > 50:
            raise ValueError("El nombre del tag no puede superar 50 caracteres.")
        return v


@router.get("/user/tags")
def list_tags(current_user: dict = Depends(get_current_user)):
    return {"tags": get_tags(user_id=current_user["user_id"])}


@router.post("/user/tags", status_code=201)
def add_tag(body: TagIn, current_user: dict = Depends(get_current_user)):
    tag = create_tag(user_id=current_user["user_id"], name=body.name)
    if tag is None:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "TAG_ALREADY_EXISTS", "message": "Ya existe un tag con ese nombre."},
        )
    return tag


@router.delete("/user/tags/{tag_id}", status_code=200)
def remove_tag(tag_id: str, current_user: dict = Depends(get_current_user)):
    deleted = delete_tag(tag_id=tag_id, user_id=current_user["user_id"])
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "TAG_NOT_FOUND", "message": "Tag no encontrado."},
        )
    return {"message": "Tag eliminado correctamente."}
