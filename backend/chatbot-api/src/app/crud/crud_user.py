from typing import Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserInDB
from app.core.security import get_password_hash, verify_password

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class CRUDUser:
    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        """Get a user by username"""
        return db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get a user by email"""
        return db.query(User).filter(User.email == email).first()
    
    def get(self, db: Session, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> list[User]:
        """Get multiple users with pagination"""
        return db.query(User).offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """Create a new user"""
        hashed_password = get_password_hash(obj_in.password)
        db_user = User(
            username=obj_in.username,
            email=obj_in.email,
            hashed_password=hashed_password,
            full_name=obj_in.full_name,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    def update(
        self, db: Session, *, db_user: User, obj_in: UserUpdate
    ) -> User:
        """Update a user"""
        update_data = obj_in.dict(exclude_unset=True)
        if "password" in update_data:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    def authenticate(self, db: Session, *, username: str, password: str) -> Optional[User]:
        """Authenticate a user"""
        user = self.get_by_username(db, username=username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def is_active(self, user: User) -> bool:
        """Check if a user is active"""
        return user.is_active
    
    def is_superuser(self, user: User) -> bool:
        """Check if a user is a superuser (admin)"""
        return user.role == UserRole.ADMIN

# Create a singleton instance
user = CRUDUser()
