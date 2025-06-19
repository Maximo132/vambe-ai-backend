"""
Modelos de seguridad para la autenticación y autorización.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class TokenData(BaseModel):
    """Modelo de datos para el token JWT"""
    sub: str
    scopes: List[str] = []
    exp: datetime
    iat: datetime = datetime.utcnow()
    jti: str 
    user_id: str
    is_superuser: bool = False
    is_active: bool = True

class Token(BaseModel):
    """Modelo de respuesta para el token de acceso"""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    user_id: str
    is_superuser: bool

class TokenPayload(BaseModel):
    """Payload del token JWT"""
    sub: str
    exp: datetime
    iat: datetime
    jti: str
    user_id: str
    is_superuser: bool = False
    is_active: bool = True
    scopes: List[str] = []

class UserInDB(BaseModel):
    """Modelo de usuario en la base de datos"""
    id: str
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    role: str
    hashed_password: str
