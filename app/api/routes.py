from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.api.auth import api_register, api_login, api_refresh, api_logout
from app.api.analysis import api_upload, api_manual
from app.api.alerts import api_send
from app.api.user import api_contacts
from app.api.history import api_summary, api_detail, api_delete

# Router público — solo health, register y login
public_router = APIRouter()
public_router.include_router(api_register.router)
public_router.include_router(api_login.router)

# Router protegido — todo lo demás requiere JWT válido
protected_router = APIRouter(dependencies=[Depends(get_current_user)])
protected_router.include_router(api_refresh.router)
protected_router.include_router(api_logout.router)
protected_router.include_router(api_upload.router)
protected_router.include_router(api_manual.router)
protected_router.include_router(api_send.router)
protected_router.include_router(api_contacts.router)
protected_router.include_router(api_summary.router)
protected_router.include_router(api_detail.router)
protected_router.include_router(api_delete.router)
