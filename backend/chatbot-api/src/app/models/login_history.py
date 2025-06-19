"""
Modelo para el historial de inicios de sesión de los usuarios.
"""
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import INET

from .base import Base

class LoginHistory(Base):
    """
    Modelo para registrar el historial de inicios de sesión de los usuarios.
    """
    __tablename__ = "login_history"
    
    # Identificación
    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Información de la sesión
    ip_address = Column(String(45), nullable=True)  # IPv6 puede tener hasta 45 caracteres
    user_agent = Column(Text, nullable=True)
    device_id = Column(String(255), nullable=True, index=True)
    device_name = Column(String(100), nullable=True)
    device_type = Column(String(50), nullable=True)  # mobile, tablet, desktop, bot, etc.
    
    # Ubicación (se puede obtener de servicios como MaxMind o similar)
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    location_data = Column(JSON, nullable=True)  # Datos crudos de geolocalización
    
    # Información de la aplicación
    client_name = Column(String(100), nullable=True)  # Nombre de la aplicación cliente
    client_version = Column(String(50), nullable=True)  # Versión de la aplicación cliente
    
    # Estado de la autenticación
    status = Column(String(20), nullable=False, index=True)  # success, failed, blocked, etc.
    failure_reason = Column(Text, nullable=True)  # Razón del fallo si lo hubo
    
    # Información de seguridad
    is_2fa_used = Column(Boolean, default=False, nullable=False)
    is_remember_me = Column(Boolean, default=False, nullable=False)
    
    # Auditoría
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)  # Para limpieza automática
    
    # Relaciones
    user = relationship("User", back_populates="login_history")
    
    # Índices
    __table_args__ = (
        Index('idx_login_history_user_status', 'user_id', 'status'),
        Index('idx_login_history_created_at', 'created_at'),
        Index('idx_login_history_device', 'device_id', 'user_id'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el objeto a un diccionario.
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'country': self.country,
            'region': self.region,
            'city': self.city,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_2fa_used': self.is_2fa_used,
            'is_remember_me': self.is_remember_me,
        }
    
    @classmethod
    def create_login_attempt(
        cls,
        user_id: str,
        ip_address: str = None,
        user_agent: str = None,
        device_id: str = None,
        status: str = "success",
        failure_reason: str = None,
        is_2fa_used: bool = False,
        is_remember_me: bool = False,
        **kwargs
    ) -> 'LoginHistory':
        """
        Crea un nuevo registro de intento de inicio de sesión.
        """
        from sqlalchemy.orm import Session
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            login = cls(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                device_id=device_id,
                status=status,
                failure_reason=failure_reason,
                is_2fa_used=is_2fa_used,
                is_remember_me=is_remember_me,
                **kwargs
            )
            
            # Establecer fecha de expiración (por defecto 1 año)
            login.expires_at = datetime.utcnow() + timedelta(days=365)
            
            db.add(login)
            db.commit()
            db.refresh(login)
            return login
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    @classmethod
    def get_user_login_history(
        cls,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
        status: str = None,
        device_id: str = None
    ) -> list['LoginHistory']:
        """
        Obtiene el historial de inicios de sesión de un usuario.
        """
        from sqlalchemy.orm import Session
        from sqlalchemy import desc
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            query = db.query(cls).filter(cls.user_id == user_id)
            
            if status:
                query = query.filter(cls.status == status)
                
            if device_id:
                query = query.filter(cls.device_id == device_id)
            
            return query.order_by(desc(cls.created_at)).offset(offset).limit(limit).all()
        finally:
            db.close()
    
    @classmethod
    def get_recent_failed_attempts(
        cls,
        user_id: str,
        minutes: int = 15,
        ip_address: str = None
    ) -> int:
        """
        Obtiene el número de intentos fallidos recientes para un usuario.
        """
        from sqlalchemy.orm import Session
        from sqlalchemy import func, and_
        from datetime import datetime, timedelta
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            time_threshold = datetime.utcnow() - timedelta(minutes=minutes)
            
            query = db.query(func.count(cls.id)).filter(
                cls.user_id == user_id,
                cls.status == 'failed',
                cls.created_at >= time_threshold
            )
            
            if ip_address:
                query = query.filter(cls.ip_address == ip_address)
            
            return query.scalar() or 0
        finally:
            db.close()
    
    @classmethod
    def revoke_sessions(
        cls,
        user_id: str,
        device_id: str = None,
        revoke_all: bool = False
    ) -> int:
        """
        Revoca las sesiones activas de un usuario.
        
        Args:
            user_id: ID del usuario
            device_id: ID del dispositivo a revocar (opcional)
            revoke_all: Si es True, revoca todas las sesiones del usuario
            
        Returns:
            int: Número de sesiones revocadas
        """
        from sqlalchemy.orm import Session
        from sqlalchemy import update
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        try:
            # En un sistema real, aquí marcaríamos los tokens como revocados
            # o los eliminaríamos de la base de datos de tokens activos
            # Este es un ejemplo simplificado
            
            # En una implementación real, podríamos usar Redis o una tabla de tokens revocados
            # Para este ejemplo, simplemente actualizamos el estado en la base de datos
            
            query = db.query(cls).filter(
                cls.user_id == user_id,
                cls.status == 'success',
                (cls.expires_at.is_(None) | (cls.expires_at > datetime.utcnow()))
            )
            
            if device_id and not revoke_all:
                query = query.filter(cls.device_id == device_id)
            
            # Marcar como expiradas las sesiones
            updated = query.update(
                {'expires_at': datetime.utcnow()},
                synchronize_session=False
            )
            
            db.commit()
            return updated
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def __repr__(self) -> str:
        return f"<LoginHistory {self.id} - {self.user_id} - {self.status} - {self.created_at}>"
