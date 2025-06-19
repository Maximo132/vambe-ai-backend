"""
Módulo de seguridad para la autenticación y autorización de usuarios.
Incluye funciones para el manejo de contraseñas, generación de tokens JWT,
verificación de tokens y gestión de autenticación.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union, List
import secrets
import string
import bcrypt

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError

from ..core.config import settings
from ..db.session import get_db, Session
from ..schemas.token import TokenData, Token, TokenPayload, UserInDB
from ..models.user import User, UserRole
from ..crud.crud_user import user as crud_user

# Constantes
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 100
TOKEN_URL = "api/v1/auth/login"

# Configuración de seguridad
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=TOKEN_URL)
http_bearer = HTTPBearer(auto_error=False)

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
    scopes: List[str] = []

class TokenPayload(BaseModel):
    """Payload del token JWT"""
    sub: str  # username or email
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
    role: UserRole
    hashed_password: str
    
    class Config:
        from_attributes = True

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si la contraseña en texto plano coincide con el hash almacenado.
    
    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash de la contraseña almacenado
        
    Returns:
        bool: True si la contraseña es válida, False en caso contrario
    """
    if not plain_password or not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """
    Genera un hash seguro de la contraseña.
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        str: Hash de la contraseña
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def generate_secure_password(length: int = 16) -> str:
    """
    Genera una contraseña aleatoria segura.
    
    Args:
        length: Longitud de la contraseña (por defecto: 16)
        
    Returns:
        str: Contraseña generada
    """
    if length < 8:
        raise ValueError("La longitud mínima de la contraseña debe ser 8 caracteres")
        
    # Caracteres permitidos
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    special = '!@#$%^&*()_+-=[]{}|;:,.<>?'
    
    # Asegurarse de que la contraseña contenga al menos un carácter de cada tipo
    password = [
        secrets.choice(lower),
        secrets.choice(upper),
        secrets.choice(digits),
        secrets.choice(special)
    ]
    
    # Completar con caracteres aleatorios
    all_chars = lower + upper + digits + special
    password.extend(secrets.choice(all_chars) for _ in range(length - 4))
    
    # Mezclar los caracteres
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)

def validate_password_strength(password: str) -> bool:
    """
    Valida la fortaleza de una contraseña.
    
    Requisitos mínimos:
    - Al menos 8 caracteres
    - Al menos una letra minúscula
    - Al menos una letra mayúscula
    - Al menos un número
    - Al menos un carácter especial
    
    Args:
        password: Contraseña a validar
        
    Returns:
        bool: True si la contraseña cumple con los requisitos, False en caso contrario
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return False
    if len(password) > PASSWORD_MAX_LENGTH:
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(c in string.punctuation for c in password):
        return False
    return True

def create_access_token(
    subject: Union[str, Any], 
    user_id: str,
    expires_delta: Optional[timedelta] = None,
    scopes: Optional[List[str]] = None,
    is_superuser: bool = False,
    is_active: bool = True
) -> str:
    """
    Crea un token JWT de acceso.
    
    Args:
        subject: Identificador del sujeto (usualmente el username o email)
        user_id: ID del usuario
        expires_delta: Tiempo de expiración del token
        scopes: Lista de alcances (scopes) del token
        is_superuser: Indica si el usuario es superusuario
        is_active: Indica si el usuario está activo
        
    Returns:
        str: Token JWT codificado
    """
    if scopes is None:
        scopes = []
        
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Identificador único para el token (JWT ID)
    jti = secrets.token_urlsafe(32)
    
    to_encode = {
        "iss": settings.APP_NAME,
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "jti": jti,
        "user_id": str(user_id),
        "is_superuser": is_superuser,
        "is_active": is_active,
        "scopes": scopes
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def create_refresh_token(
    subject: Union[str, Any],
    user_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un token de refresco.
    
    Args:
        subject: Identificador del sujeto (usualmente el username o email)
        user_id: ID del usuario
        expires_delta: Tiempo de expiración del token
        
    Returns:
        str: Token de refresco JWT codificado
    """
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Identificador único para el token (JWT ID)
    jti = secrets.token_urlsafe(32)
    
    to_encode = {
        "iss": settings.APP_NAME,
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "jti": jti,
        "user_id": str(user_id),
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_REFRESH_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def create_tokens(
    user_id: str,
    subject: Union[str, Any],
    is_superuser: bool = False,
    is_active: bool = True,
    scopes: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Crea tokens de acceso y de refresco.
    
    Args:
        user_id: ID del usuario
        subject: Identificador del sujeto (usualmente el username o email)
        is_superuser: Indica si el usuario es superusuario
        is_active: Indica si el usuario está activo
        scopes: Lista de alcances (scopes) del token
        
    Returns:
        Dict[str, str]: Diccionario con access_token y refresh_token
    """
    if scopes is None:
        scopes = []
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        subject=subject,
        user_id=user_id,
        expires_delta=access_token_expires,
        scopes=scopes,
        is_superuser=is_superuser,
        is_active=is_active
    )
    
    refresh_token = create_refresh_token(
        subject=subject,
        user_id=user_id,
        expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
        "user_id": user_id,
        "is_superuser": is_superuser,
        "scopes": scopes
    }

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
    db: Session = Depends(get_db)
) -> User:
    """
    Obtiene el usuario actual a partir del token JWT.
    
    Args:
        credentials: Credenciales de autenticación (Bearer token)
        db: Sesión de base de datos
        
    Returns:
        User: Instancia del usuario autenticado
        
    Raises:
        HTTPException: Si el token no es válido o el usuario no existe
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionaron credenciales",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        
        # Validar el payload del token
        try:
            token_data = TokenPayload(**payload)
        except ValidationError:
            raise credentials_exception
            
        user_id = token_data.user_id
        if user_id is None:
            raise credentials_exception
            
        # Verificar si el token está en la lista negra (logout)
        # Esto requiere implementar un sistema de revocación de tokens
        # if is_token_revoked(payload["jti"]):
        #     raise credentials_exception
            
    except JWTError as e:
        logger.error(f"Error al decodificar el token: {str(e)}")
        raise credentials_exception
    
    # Obtener el usuario de la base de datos
    user = crud_user.get(db, id=user_id)
    if user is None:
        raise credentials_exception
        
    # Verificar si el usuario está activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Obtiene el usuario actual si está activo.
    
    Args:
        current_user: Usuario autenticado
        
    Returns:
        User: Usuario activo
        
    Raises:
        HTTPException: Si el usuario está inactivo
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Obtiene el usuario actual si es superusuario.
    
    Args:
        current_user: Usuario autenticado
        
    Returns:
        User: Usuario superusuario
        
    Raises:
        HTTPException: Si el usuario no es superusuario
    """
    if not current_user.role == UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene suficientes privilegios"
        )
    return current_user

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verifica un token JWT y devuelve su payload.
    
    Args:
        token: Token JWT a verificar
        
    Returns:
        Dict[str, Any]: Payload del token
        
    Raises:
        HTTPException: Si el token no es válido
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        return payload
    except JWTError as e:
        logger.error(f"Error al verificar el token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_token_from_request(request: Request) -> Optional[str]:
    """
    Extrae el token de la cabecera de autorización de la solicitud.
    
    Args:
        request: Objeto Request de FastAPI
        
    Returns:
        Optional[str]: Token JWT o None si no se encuentra
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None
