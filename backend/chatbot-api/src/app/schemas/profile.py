"""
Esquemas para la gestión de perfiles de usuario.
"""
from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ProfileBase(BaseModel):
    """Datos básicos del perfil de usuario."""
    full_name: Optional[str] = Field(None, description="Nombre completo del usuario")
    bio: Optional[str] = Field(None, max_length=500, description="Biografía o descripción del perfil")
    phone: Optional[str] = Field(None, description="Número de teléfono")
    location: Optional[str] = Field(None, description="Ubicación del usuario")
    website: Optional[HttpUrl] = Field(None, description="Sitio web personal o profesional")
    date_of_birth: Optional[datetime] = Field(None, description="Fecha de nacimiento")
    
    @validator('phone')
    def validate_phone(cls, v):
        if v is not None and not v.replace('+', '').replace(' ', '').isdigit():
            raise ValueError("El número de teléfono debe contener solo dígitos y el símbolo '+'")
        return v

class ProfileCreate(ProfileBase):
    """Esquema para la creación de un perfil."""
    pass

class ProfileUpdate(ProfileBase):
    """Esquema para actualizar un perfil."""
    email: Optional[EmailStr] = Field(None, description="Nuevo correo electrónico")

class ProfileResponse(ProfileBase):
    """Respuesta del perfil de usuario."""
    user_id: str
    email: EmailStr
    username: str
    is_verified: bool
    is_active: bool
    role: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class PasswordChange(BaseModel):
    """Esquema para el cambio de contraseña."""
    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña (mínimo 8 caracteres)")
    confirm_password: str = Field(..., description="Confirmación de la nueva contraseña")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v

class AvatarResponse(BaseModel):
    """Respuesta para la carga de avatar."""
    avatar_url: str = Field(..., description="URL del avatar subido")
    message: str = Field(..., description="Mensaje descriptivo")

class NotificationSettings(BaseModel):
    """Configuración de notificaciones del usuario."""
    email_notifications: bool = Field(True, description="Habilitar notificaciones por correo")
    push_notifications: bool = Field(True, description="Habilitar notificaciones push")
    message_notifications: bool = Field(True, description="Notificaciones de mensajes")
    mention_notifications: bool = Field(True, description="Notificaciones de menciones")
    newsletter: bool = Field(False, description="Recibir boletines informativos")
