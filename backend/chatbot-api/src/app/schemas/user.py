from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum

from app.models.user import UserRole

class UserBase(BaseModel):
    """Base schema for user data.
    
    Attributes:
        email: Email del usuario
        full_name: Nombre completo (opcional)
        is_active: Indica si el usuario está activo
        role: Rol del usuario (admin, operator, client)
    """
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    role: Optional[UserRole] = UserRole.CLIENT

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "full_name": "Nombre Apellido",
                "is_active": True,
                "role": "client"
            }
        }

class UserCreate(UserBase):
    """Schema para la creación de un nuevo usuario.
    
    Incluye validación de contraseña segura.
    """
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(char.isdigit() for char in v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not any(char.isupper() for char in v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "full_name": "Nombre Apellido",
                "password": "Contraseña123",
                "is_active": True,
                "role": "client"
            }
        }

class UserUpdate(BaseModel):
    """Schema para actualizar datos de usuario.
    
    Todos los campos son opcionales.
    """
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    
    @validator('password')
    def password_must_be_strong(cls, v):
        if v is not None:
            if len(v) < 8:
                raise ValueError('La contraseña debe tener al menos 8 caracteres')
            if not any(char.isdigit() for char in v):
                raise ValueError('La contraseña debe contener al menos un número')
            if not any(char.isupper() for char in v):
                raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "nuevo@ejemplo.com",
                "full_name": "Nuevo Nombre",
                "password": "NuevaContraseña123",
                "is_active": True,
                "role": "operator"
            }
        }

class UserInDBBase(UserBase):
    """Base schema para datos de usuario en la base de datos.
    
    Incluye campos de auditoría.
    """
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class User(UserInDBBase):
    """Schema para devolver datos de usuario (sin información sensible)."""
    pass

class UserInDB(UserInDBBase):
    """Schema para datos de usuario en la base de datos (incluye contraseña hasheada)."""
    hashed_password: str

class UserLogin(BaseModel):
    """Schema para el inicio de sesión de usuario."""
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "password": "Contraseña123"
            }
        }

class Token(BaseModel):
    """Schema para el token de autenticación."""
    access_token: str
    token_type: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }

class TokenData(BaseModel):
    """Datos contenidos en el token JWT."""
    email: Optional[str] = None
    scopes: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "scopes": ["me", "items"]
            }
        }
