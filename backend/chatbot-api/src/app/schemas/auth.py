from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []

class Message(BaseModel):
    message: str

class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    AGENT = "agent"
    CUSTOMER = "customer"
    GUEST = "guest"

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    role: UserRole = UserRole.CUSTOMER

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str
    remember_me: bool = False

class UserInDB(UserBase):
    id: int
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class UserResponse(UserInDB):
    pass

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class TwoFactorSetupResponse(BaseModel):
    qr_code: str
    secret: str
    manual_entry_code: str
    verification_required: bool = True

class TwoFactorVerify(BaseModel):
    code: str

class TwoFactorBackupCodes(BaseModel):
    backup_codes: List[str]

class DeviceInfo(BaseModel):
    device_id: str
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

class SessionInfo(BaseModel):
    id: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: datetime
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_current: bool = False

class OAuth2Provider(str, Enum):
    GOOGLE = "google"
    FACEBOOK = "facebook"
    GITHUB = "github"
    LINKEDIN = "linkedin"

class OAuth2Token(BaseModel):
    token: str
    provider: OAuth2Provider

class OAuth2UserInfo(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None
    verified_email: Optional[bool] = None
