"""
Modelo para gestionar los tokens de autenticación y sesiones de usuario.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uuid
import json

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base
from app.core.config import settings

class AuthToken(Base):
    """
    Modelo para almacenar tokens de autenticación y sesiones de usuario.
    
    Este modelo permite:
    - Rastrear sesiones activas
    - Revocar tokens individualmente
    - Almacenar metadatos de la sesión
    - Implementar "cerrar sesión en todos los dispositivos"
    """
    __tablename__ = "auth_tokens"
    
    # Identificación
    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Información del token
    token = Column(String(500), unique=True, nullable=False, index=True)
    refresh_token = Column(String(500), unique=True, nullable=True, index=True)
    token_type = Column(String(20), default="bearer", nullable=False)  # bearer, api_key, etc.
    scopes = Column(JSONB, default=list, nullable=False)  # Lista de permisos/alcances
    
    # Información de la sesión
    device_id = Column(String(255), nullable=True, index=True)
    device_name = Column(String(100), nullable=True)
    device_type = Column(String(50), nullable=True)  # web, mobile, desktop, etc.
    ip_address = Column(String(45), nullable=True)  # IPv6 puede tener hasta 45 caracteres
    user_agent = Column(Text, nullable=True)
    
    # Ubicación
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    location_data = Column(JSONB, nullable=True)  # Datos crudos de geolocalización
    
    # Estado y fechas
    is_revoked = Column(Boolean, default=False, nullable=False, index=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    user = relationship("User", back_populates="auth_tokens")
    
    # Índices
    __table_args__ = (
        Index('idx_auth_token_user_device', 'user_id', 'device_id'),
        Index('idx_auth_token_expires', 'expires_at'),
        Index('idx_auth_token_user_status', 'user_id', 'is_revoked'),
    )
    
    @property
    def is_expired(self) -> bool:
        """Verifica si el token ha expirado."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_active(self) -> bool:
        """Verifica si el token está activo (no revocado y no expirado)."""
        return not self.is_revoked and not self.is_expired
    
    def revoke(self) -> None:
        """Revoca el token."""
        self.is_revoked = True
        self.updated_at = datetime.utcnow()
    
    def extend(self, expires_delta: Optional[timedelta] = None) -> None:
        """Extiende la vida útil del token."""
        if expires_delta is None:
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self.expires_at = datetime.utcnow() + expires_delta
        self.updated_at = datetime.utcnow()
    
    def update_usage(self, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        """Actualiza la información de uso del token."""
        self.last_used_at = datetime.utcnow()
        if ip_address:
            self.ip_address = ip_address
        if user_agent:
            self.user_agent = user_agent
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el objeto a un diccionario."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'token_type': self.token_type,
            'scopes': self.scopes,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'ip_address': self.ip_address,
            'country': self.country,
            'region': self.region,
            'city': self.city,
            'is_revoked': self.is_revoked,
            'is_expired': self.is_expired,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def create_token(
        cls,
        user_id: str,
        token: str,
        refresh_token: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        expires_delta: Optional[timedelta] = None,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ) -> 'AuthToken':
        """
        Crea un nuevo token de autenticación.
        """
        from sqlalchemy.orm import Session
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            if expires_delta is None:
                expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            
            auth_token = cls(
                user_id=user_id,
                token=token,
                refresh_token=refresh_token,
                scopes=scopes or [],
                device_id=device_id,
                device_name=device_name,
                device_type=device_type,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.utcnow() + expires_delta,
                **kwargs
            )
            
            db.add(auth_token)
            db.commit()
            db.refresh(auth_token)
            return auth_token
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    @classmethod
    def get_active_token(
        cls,
        token: str,
        token_type: str = "access"
    ) -> Optional['AuthToken']:
        """
        Obtiene un token activo por su valor.
        """
        from sqlalchemy.orm import Session
        from sqlalchemy import or_, and_
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            
            query = db.query(cls).filter(
                or_(
                    and_(
                        cls.token == token,
                        token_type == "access"
                    ),
                    and_(
                        cls.refresh_token == token,
                        token_type == "refresh"
                    )
                ),
                cls.is_revoked == False,
                cls.expires_at > now
            )
            
            return query.first()
        finally:
            db.close()
    
    @classmethod
    def revoke_token(
        cls,
        token: str,
        token_type: str = "access"
    ) -> bool:
        """
        Revoca un token por su valor.
        """
        from sqlalchemy.orm import Session
        from sqlalchemy import or_, and_
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            
            token_obj = db.query(cls).filter(
                or_(
                    and_(
                        cls.token == token,
                        token_type == "access"
                    ),
                    and_(
                        cls.refresh_token == token,
                        token_type == "refresh"
                    )
                ),
                cls.is_revoked == False,
                cls.expires_at > now
            ).first()
            
            if token_obj:
                token_obj.revoke()
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    @classmethod
    def revoke_all_user_tokens(
        cls,
        user_id: str,
        exclude_token: Optional[str] = None,
        token_type: str = "access"
    ) -> int:
        """
        Revoca todos los tokens de un usuario, opcionalmente excluyendo uno.
        """
        from sqlalchemy.orm import Session
        from sqlalchemy import and_, or_
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            
            query = db.query(cls).filter(
                cls.user_id == user_id,
                cls.is_revoked == False,
                cls.expires_at > now
            )
            
            if exclude_token:
                if token_type == "access":
                    query = query.filter(cls.token != exclude_token)
                else:
                    query = query.filter(cls.refresh_token != exclude_token)
            
            updated = query.update(
                {'is_revoked': True, 'updated_at': now},
                synchronize_session=False
            )
            
            db.commit()
            return updated
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    @classmethod
    def cleanup_expired_tokens(cls, batch_size: int = 1000) -> int:
        """
        Elimina tokens expirados de la base de datos.
        """
        from sqlalchemy.orm import Session
        from sqlalchemy import or_
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            
            # Primero obtenemos los IDs de los tokens a eliminar
            expired_tokens = db.query(cls.id).filter(
                or_(
                    cls.expires_at <= now,
                    cls.is_revoked == True
                )
            ).limit(batch_size).all()
            
            if not expired_tokens:
                return 0
                
            # Convertir a lista de IDs
            token_ids = [t[0] for t in expired_tokens]
            
            # Eliminar en lotes para evitar bloqueos
            deleted = db.query(cls).filter(cls.id.in_(token_ids)).delete(synchronize_session=False)
            db.commit()
            
            return deleted
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def __repr__(self) -> str:
        return f"<AuthToken {self.id} - {self.user_id} - {self.device_name} - {'active' if self.is_active else 'inactive'}>"


# Añadir la relación al modelo User
def add_auth_token_relationship():
    """
    Función para añadir la relación con AuthToken al modelo User.
    Esto evita problemas de importación circular.
    """
    from app.models.user import User
    
    if not hasattr(User, 'auth_tokens'):
        User.auth_tokens = relationship(
            "AuthToken",
            back_populates="user",
            cascade="all, delete-orphan"
        )

# Llamar a la función para establecer la relación
add_auth_token_relationship()
