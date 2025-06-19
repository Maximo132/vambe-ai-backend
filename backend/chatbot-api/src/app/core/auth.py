"""
Módulo para la autenticación y autorización de usuarios.

Este módulo proporciona funciones para autenticar usuarios, verificar tokens JWT,
generar tokens de acceso y refresco, y gestionar la autorización de usuarios.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from ..db.database import get_db
from ..models.user import User

# Configuración de seguridad
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

# Constantes para tokens
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con un hash.
    
    Args:
        plain_password: Contraseña en texto plano.
        hashed_password: Hash de la contraseña almacenado.
        
    Returns:
        bool: True si la contraseña es válida, False en caso contrario.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera un hash seguro de una contraseña.
    
    Args:
        password: Contraseña en texto plano.
        
    Returns:
        str: Hash de la contraseña.
    """
    return pwd_context.hash(password)


async def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
    """
    Autentica a un usuario con su correo electrónico y contraseña.
    
    Args:
        email: Correo electrónico del usuario.
        password: Contraseña en texto plano.
        db: Sesión de base de datos.
        
    Returns:
        Optional[User]: El usuario autenticado o None si la autenticación falla.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un token de acceso JWT.
    
    Args:
        data: Datos a incluir en el token.
        expires_delta: Tiempo de expiración del token. Si es None, se usa el valor por defecto.
        
    Returns:
        str: Token JWT codificado.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un token de refresco JWT.
    
    Args:
        user_id: ID del usuario.
        expires_delta: Tiempo de expiración del token. Si es None, se usa el valor por defecto.
        
    Returns:
        str: Token de refresco JWT codificado.
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Obtiene el usuario actual a partir del token JWT.
    
    Args:
        token: Token JWT.
        db: Sesión de base de datos.
        
    Returns:
        User: El usuario autenticado.
        
    Raises:
        HTTPException: Si el token no es válido o el usuario no existe.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Obtiene el usuario actual activo.
    
    Args:
        current_user: Usuario actual obtenido del token JWT.
        
    Returns:
        User: El usuario activo.
        
    Raises:
        HTTPException: Si el usuario está inactivo.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user


def has_role(required_roles: list[str]):
    """
    Verifica si el usuario tiene alguno de los roles requeridos.
    
    Args:
        required_roles: Lista de roles permitidos.
        
    Returns:
        callable: Función que verifica los roles del usuario.
    """
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role.name not in required_roles and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos suficientes para realizar esta acción",
            )
        return current_user
    return role_checker
