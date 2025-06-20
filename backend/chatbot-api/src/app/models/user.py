from sqlalchemy import Boolean, Column, String, DateTime, Enum, Integer, Text, JSON, Table, ForeignKey
from sqlalchemy.orm import relationship, Session, backref
from sqlalchemy.sql import func, and_, or_
from sqlalchemy.sql.schema import Index
from app.models.base import Base
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, TYPE_CHECKING, Set
import uuid
import logging
import json
import bcrypt
from email_validator import validate_email, EmailNotValidError

if TYPE_CHECKING:
    from .document import Document  # Para type hints sin importación circular
    from .conversation import Conversation  # Para type hints sin importación circular
    from .message import Message  # Para type hints sin importación circular

logger = logging.getLogger(__name__)

# Tabla de asociación para la relación muchos a muchos entre usuarios (seguidores/seguidos)
user_followers = Table(
    'user_followers',
    Base.metadata,
    Column('follower_id', String(36), ForeignKey('users.id'), primary_key=True),
    Column('followed_id', String(36), ForeignKey('users.id'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow)
)

from .enums import UserRole

class User(Base):
    """Modelo de usuario para autenticación y gestión de perfiles"""
    __tablename__ = "users"
    
    # Identificación
    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    external_id = Column(String(100), unique=True, index=True, nullable=True)  # Para integraciones externas
    
    @staticmethod
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
    
    def verify_password(self, plain_password: str) -> bool:
        """
        Verifica si la contraseña en texto plano coincide con el hash almacenado.
        
        Args:
            plain_password: Contraseña en texto plano
            
        Returns:
            bool: True si la contraseña es válida, False en caso contrario
        """
        if not self.hashed_password:
            return False
        return bcrypt.checkpw(plain_password.encode('utf-8'), self.hashed_password.encode('utf-8'))
    
    # Autenticación
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    email_verified = Column(Boolean(), default=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Información del perfil
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(201), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    def update_full_name(self) -> None:
        """Actualiza el campo full_name basado en first_name y last_name"""
        if self.first_name and self.last_name:
            self.full_name = f"{self.first_name} {self.last_name}"
        elif self.first_name:
            self.full_name = self.first_name
        elif self.last_name:
            self.full_name = self.last_name
        else:
            self.full_name = ""
    
    # Preferencias
    preferences = Column(JSON, default=dict, nullable=True)
    settings = Column(JSON, default=dict, nullable=True)
    
    # Estado y roles
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    is_active = Column(Boolean(), default=True)
    is_verified = Column(Boolean(), default=False)
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    
    # Control de acceso
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # Auditoría
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relaciones
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    login_history = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    auth_tokens = relationship("AuthToken", back_populates="user", cascade="all, delete-orphan")
    
    # Relación muchos a muchos para seguidores/seguidos
    followed = relationship(
        'User', 
        secondary=user_followers,
        primaryjoin=(user_followers.c.follower_id == id),
        secondaryjoin=(user_followers.c.followed_id == id),
        backref=relationship(
            'followers',
            lazy='dynamic',
            primaryjoin=(user_followers.c.followed_id == id),
            secondaryjoin=(user_followers.c.follower_id == id)
        ),
        lazy='dynamic',
        viewonly=True
    )
    
    # Tokens de verificación y restablecimiento
    verification_token = Column(String(100), unique=True, nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    password_reset_token = Column(String(100), unique=True, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    
    # Configuración de seguridad
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(255), nullable=True)
    backup_codes = Column(JSON, nullable=True)  # Códigos de respaldo para 2FA
    
    # Preferencias de notificación
    email_notifications = Column(Boolean, default=True, nullable=False)
    push_notifications = Column(Boolean, default=True, nullable=False)
    sms_notifications = Column(Boolean, default=False, nullable=False)
    
    # Métadatos de seguridad
    last_password_change = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, nullable=True)
    last_ip_address = Column(String(45), nullable=True)  # IPv6 puede tener hasta 45 caracteres
    
    # Sesiones activas (simplificado - en producción usaría Redis o similar)
    active_sessions = Column(JSON, default=list, nullable=True)  # Lista de tokens de sesión activos
    
    # Preferencias de privacidad
    show_online_status = Column(Boolean, default=True, nullable=False)
    allow_direct_messages = Column(Boolean, default=True, nullable=False)
    
    # Tema de la interfaz
    theme = Column(String(20), default='system', nullable=False)  # 'light', 'dark', 'system'
    
    # Índices
    __table_args__ = (
        Index('idx_user_email_lower', func.lower(email), unique=True),
        Index('idx_user_username_lower', func.lower(username), unique=True),
        Index('idx_user_created_at', 'created_at'),
        Index('idx_user_role', 'role'),
        Index('idx_user_status', 'is_active', 'is_verified'),
    )

    # Métodos de utilidad
    def set_password(self, password: str) -> None:
        """Establece la contraseña del usuario"""
        self.hashed_password = get_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verifica si la contraseña es correcta"""
        return verify_password(password, self.hashed_password)
    
    def is_locked(self) -> bool:
        """Verifica si la cuenta está bloqueada temporalmente"""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until
    
    def lock_account(self, minutes: int = 30) -> None:
        """Bloquea la cuenta por el número de minutos especificado"""
        self.locked_until = datetime.utcnow() + timedelta(minutes=minutes)
    
    def unlock_account(self) -> None:
        """Desbloquea la cuenta"""
        self.locked_until = None
        self.failed_login_attempts = 0
    
    def record_login(self) -> None:
        """Registra un inicio de sesión exitoso"""
        self.last_login = datetime.utcnow()
        self.login_count += 1
        self.failed_login_attempts = 0
        if self.is_locked():
            self.unlock_account()
    
    def record_failed_login(self) -> None:
        """Registra un intento de inicio de sesión fallido"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:  # Bloquear después de 5 intentos fallidos
            self.lock_account()
    
    def has_permission(self, permission: str) -> bool:
        """Verifica si el usuario tiene un permiso específico"""
        # Implementar lógica de permisos según el rol
        if self.role == UserRole.SUPERADMIN:
            return True
        # Agregar más lógica de permisos según sea necesario
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el objeto de usuario a un diccionario"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'avatar_url': self.avatar_url,
            'role': self.role.value,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    # Métodos para manejar seguidores/seguidos
    def follow(self, user: 'User') -> None:
        """Seguir a otro usuario"""
        if not self.is_following(user):
            self.followed.append(user)
    
    def unfollow(self, user: 'User') -> None:
        """Dejar de seguir a otro usuario"""
        if self.is_following(user):
            self.followed.remove(user)
    
    def is_following(self, user: 'User') -> bool:
        """Verifica si este usuario está siguiendo a otro usuario"""
        return bool(self.followed.filter(user_followers.c.followed_id == user.id).count() > 0)
    
    # Métodos de clase
    @classmethod
    def get_by_email(cls, db: Session, email: str) -> Optional['User']:
        """Obtiene un usuario por su correo electrónico (case-insensitive)"""
        return db.query(cls).filter(func.lower(cls.email) == email.lower()).first()
    
    @classmethod
    def get_by_username(cls, db: Session, username: str) -> Optional['User']:
        """Obtiene un usuario por su nombre de usuario (case-insensitive)"""
        return db.query(cls).filter(func.lower(cls.username) == username.lower()).first()
    
    @classmethod
    def authenticate(cls, db: Session, username: str, password: str) -> Optional['User']:
        """Autentica a un usuario por nombre de usuario/correo y contraseña"""
        user = cls.get_by_username(db, username) or cls.get_by_email(db, username)
        if user and user.check_password(password):
            if user.is_active and not user.is_locked():
                user.record_login()
                db.commit()
                return user
        elif user:
            user.record_failed_login()
            db.commit()
        return None
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
