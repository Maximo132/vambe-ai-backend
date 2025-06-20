"""
Dependencias comunes para los endpoints de la API.
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload

# Esquema OAuth2 para la autenticación con token
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Obtiene el usuario actual a partir del token JWT.
    
    Args:
        db: Sesión de base de datos
        token: Token JWT del encabezado de autorización
        
    Returns:
        User: Instancia del modelo de usuario
        
    Raises:
        HTTPException: Si el token no es válido o el usuario no existe
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó un token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decodificar el token JWT
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        # Obtener el usuario de la base de datos
        user = db.query(User).filter(User.id == token_data.sub).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
            
        return user
        
    except (JWTError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se pudo validar el token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Verifica que el usuario esté activo.
    
    Args:
        current_user: Usuario obtenido del token JWT
        
    Returns:
        User: Usuario activo
        
    Raises:
        HTTPException: Si el usuario está inactivo
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    return current_user

def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Verifica que el usuario sea un superusuario.
    
    Args:
        current_user: Usuario obtenido del token JWT
        
    Returns:
        User: Usuario superusuario
        
    Raises:
        HTTPException: Si el usuario no es superusuario
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario no tiene suficientes privilegios"
        )
    return current_user
