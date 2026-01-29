import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

# allow missing Authorization header (we'll handle missing case in the validator)
security = HTTPBearer(auto_error=False)

SECRET_KEY = "super-secret-key"
ALGORITHM = "HS256"

# Enable dev bypass when DEV_AUTH_BYPASS environment variable is set to '1'
DEV_BYPASS = os.getenv("DEV_AUTH_BYPASS", "0") == "1"

def validate_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None
):
    """Validate JWT unless DEV_BYPASS is enabled.

    - When DEV_BYPASS==True the function will accept requests without an Authorization header
      and will return a synthetic payload. If the caller provides `X-Dev-User` header its value
      will be used as the `sub` claim (helpful for testing different users).
    - Otherwise a valid Bearer token is required as before.
    """
    if DEV_BYPASS:
        dev_user = None
        if request is not None:
            dev_user = request.headers.get("x-dev-user")
        return {"sub": dev_user or "dev", "dev_bypass": True}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales faltantes"
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )
