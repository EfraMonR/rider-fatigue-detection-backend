from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.api.auth import api_register, api_login, api_refresh, api_logout
from app.api.analysis import api_upload, api_manual

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
