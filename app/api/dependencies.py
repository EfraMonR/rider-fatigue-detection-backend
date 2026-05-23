from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services import auth_service

_bearer = HTTPBearer(auto_error=False)

_TOKEN_EXPIRED = HTTPException(
    status_code=401,
    detail={"error_code": "TOKEN_EXPIRED", "message": "La sesión expiró. Renovando..."},
)
_TOKEN_INVALID = HTTPException(
    status_code=401,
    detail={"error_code": "TOKEN_INVALID", "message": "Token inválido o ausente."},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if not credentials:
        raise _TOKEN_INVALID

    payload = auth_service.decode_access_token(credentials.credentials)
    if payload is None:
        # python-jose lanza JWTError tanto para expirado como inválido;
        # intentamos distinguir re-decodificando sin verificar expiración
        try:
            from jose import jwt as _jwt
            from app.config import settings
            _jwt.decode(
                credentials.credentials,
                settings.JWT_SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
            raise _TOKEN_EXPIRED
        except Exception:
            raise _TOKEN_INVALID

    return {"user_id": payload["sub"]}
