from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _validate_token(token: str, settings: Settings) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None


async def optional_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    api_key: Annotated[str | None, Security(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict | None:
    """
    Authentification optionnelle :
    - JWT Bearer si JWT_ENABLED=true
    - ou clé API X-API-Key si API_KEY est définie
    """
    if not settings.jwt_enabled and not settings.api_key:
        return None

    if settings.api_key and api_key and api_key == settings.api_key:
        return {"auth": "api_key"}

    if settings.jwt_enabled and credentials:
        payload = _validate_token(credentials.credentials, settings)
        if payload:
            return payload
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT invalide ou expiré.",
        )

    if settings.jwt_enabled or settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise (Bearer JWT ou X-API-Key).",
        )
    return None
