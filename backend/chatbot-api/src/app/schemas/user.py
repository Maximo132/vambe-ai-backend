from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole

class UserBase(BaseModel):
    """Base schema for user data"""
    username: str = Field(..., min_length=3, max_length=50, regex="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    """Schema for updating user data"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None

class UserInDBBase(UserBase):
    """Base schema for user data in the database"""
    id: str
    role: UserRole = UserRole.CLIENT
    is_active: bool = True

    class Config:
        orm_mode = True

class User(UserInDBBase):
    """Schema for returning user data (without sensitive information)"""
    pass

class UserInDB(UserInDBBase):
    """Schema for user data in the database (includes hashed password)"""
    hashed_password: str

class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str

class UserRegister(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8)
    password_confirm: str

    class Config:
        schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "johndoe@example.com",
                "full_name": "John Doe",
                "password": "securepassword123",
                "password_confirm": "securepassword123"
            }
        }
