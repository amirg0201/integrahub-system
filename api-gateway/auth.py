import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

# --- CONFIGURACIÓN ---
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DEV_BYPASS = os.getenv("DEV_AUTH_BYPASS", "1") == "1"

# Esquema de seguridad
security = HTTPBearer(auto_error=False)

# Modelo de respuesta del Token
class Token(BaseModel):
    access_token: str
    token_type: str

# --- 1. FUNCIÓN PARA GENERAR EL TOKEN (Login) ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- 2. FUNCIÓN PARA VALIDAR EL TOKEN (Protección) ---
def validate_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None
):
    # Si el Bypass está activo (Variable de entorno = 1), deja pasar todo
    if DEV_BYPASS:
        return {"sub": "dev_admin", "bypass": True}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales faltantes (Se requiere Token)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )