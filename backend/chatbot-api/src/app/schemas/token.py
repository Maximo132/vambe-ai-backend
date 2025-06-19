from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, validator, HttpUrl
from pydantic.class_validators import root_validator

class TokenType(str, Enum):
    """Tipos de tokens soportados"""
    BEARER = "bearer"
    REFRESH = "refresh"
    VERIFICATION = "verification"
    PASSWORD_RESET = "password_reset"

class Token(BaseModel):
    """Esquema para la respuesta de autenticación"""
    access_token: str = Field(..., description="Token de acceso JWT")
    refresh_token: str = Field(..., description="Token de actualización para obtener nuevos tokens de acceso")
    token_type: str = Field(TokenType.BEARER, description="Tipo de token")
    expires_in: int = Field(3600, description="Tiempo de expiración en segundos")
    user_id: str = Field(..., description="ID del usuario autenticado")

class TokenPayload(BaseModel):
    """Payload del token JWT"""
    sub: Optional[str] = None  # Subject (user id)
    exp: Optional[datetime] = None  # Expiration time
    scopes: list[str] = Field(default_factory=list)  # Permisos del token

class TokenData(BaseModel):
    """Datos del usuario extraídos del token"""
    username: Optional[str] = Field(None, description="Nombre de usuario")
    user_id: Optional[str] = Field(None, description="ID del usuario")
    email: Optional[EmailStr] = Field(None, description="Correo electrónico del usuario")
    scopes: List[str] = Field(default_factory=list, description="Permisos del usuario")
    is_active: bool = Field(True, description="Indica si el usuario está activo")
    is_verified: bool = Field(False, description="Indica si el correo electrónico está verificado")
    token_type: Optional[TokenType] = Field(None, description="Tipo de token")

class UserLogin(BaseModel):
    """Esquema para el inicio de sesión"""
    username: str = Field(..., description="Nombre de usuario o correo electrónico")
    password: str = Field(..., min_length=8, description="Contraseña")
    captcha_token: Optional[str] = Field(None, description="Token de verificación CAPTCHA")

class UserBase(BaseModel):
    """Esquema base para usuarios"""
    username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario único")
    email: EmailStr = Field(..., description="Correo electrónico del usuario")
    full_name: Optional[str] = Field(None, max_length=100, description="Nombre completo del usuario")
    avatar_url: Optional[HttpUrl] = Field(None, description="URL de la imagen de perfil")

class UserCreate(UserBase):
    """Esquema para la creación de usuarios"""
    password: str = Field(..., min_length=8, description="Contraseña del usuario")
    password_confirm: str = Field(..., description="Confirmación de la contraseña")
    
    @root_validator()
    def passwords_match(cls, values):
        password = values.get('password')
        password_confirm = values.get('password_confirm')
        if password != password_confirm:
            raise ValueError('Las contraseñas no coinciden')
        return values

class UserUpdate(BaseModel):
    """Esquema para actualizar usuarios"""
    email: Optional[EmailStr] = Field(None, description="Nuevo correo electrónico")
    full_name: Optional[str] = Field(None, max_length=100, description="Nuevo nombre completo")
    avatar_url: Optional[HttpUrl] = Field(None, description="Nueva URL de la imagen de perfil")
    current_password: Optional[str] = Field(None, description="Contraseña actual (requerida para cambios sensibles)")
    new_password: Optional[str] = Field(None, min_length=8, description="Nueva contraseña")
    
    @root_validator()
    def validate_password_change(cls, values):
        new_password = values.get('new_password')
        current_password = values.get('current_password')
        
        if new_password and not current_password:
            raise ValueError('Se requiere la contraseña actual para cambiarla')
        return values

class UserInDB(UserBase):
    """Esquema para el usuario en la base de datos"""
    id: str = Field(..., description="Identificador único del usuario")
    is_active: bool = Field(True, description="Indica si el usuario está activo")
    is_verified: bool = Field(False, description="Indica si el correo electrónico está verificado")
    is_superuser: bool = Field(False, description="Indica si el usuario es superusuario")
    role: str = Field("user", description="Rol del usuario en el sistema")
    scopes: List[str] = Field(default_factory=list, description="Permisos del usuario")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creación")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Última actualización")
    last_login: Optional[datetime] = Field(None, description="Último inicio de sesión")
    login_attempts: int = Field(0, description="Número de intentos fallidos de inicio de sesión")
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class UserResponse(UserInDB):
    """Esquema para la respuesta de la API de usuarios"""
    pass

class TokenRefreshRequest(BaseModel):
    """Esquema para la solicitud de actualización de token"""
    refresh_token: str = Field(..., description="Token de actualización")

class PasswordResetRequest(BaseModel):
    """Esquema para la solicitud de restablecimiento de contraseña"""
    email: EmailStr = Field(..., description="Correo electrónico del usuario")

class PasswordResetConfirm(BaseModel):
    """Esquema para confirmar el restablecimiento de contraseña"""
    token: str = Field(..., description="Token de restablecimiento de contraseña")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")
    new_password_confirm: str = Field(..., description="Confirmación de la nueva contraseña")
    
    @root_validator()
    def passwords_match(cls, values):
        new_password = values.get('new_password')
        new_password_confirm = values.get('new_password_confirm')
        if new_password != new_password_confirm:
            raise ValueError('Las contraseñas no coinciden')
        return values

class EmailVerificationRequest(BaseModel):
    """Esquema para la solicitud de verificación de correo electrónico"""
    email: EmailStr = Field(..., description="Correo electrónico a verificar")

class EmailVerificationConfirm(BaseModel):
    """Esquema para confirmar la verificación de correo electrónico"""
    token: str = Field(..., description="Token de verificación de correo electrónico")

class LoginHistory(BaseModel):
    """Esquema para el historial de inicios de sesión"""
    id: str = Field(..., description="ID del registro de inicio de sesión")
    user_id: str = Field(..., description="ID del usuario")
    ip_address: str = Field(..., description="Dirección IP del inicio de sesión")
    user_agent: Optional[str] = Field(None, description="Agente de usuario del navegador")
    location: Optional[Dict[str, Any]] = Field(None, description="Ubicación geográfica aproximada")
    status: str = Field(..., description="Estado del inicio de sesión (success, failed, etc.)")
    created_at: datetime = Field(..., description="Fecha y hora del inicio de sesión")
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
