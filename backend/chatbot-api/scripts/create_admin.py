"""
Script para crear un usuario administrador por defecto.

Este script crea un usuario administrador con credenciales por defecto
y lo guarda en la base de datos.
"""
import os
import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.core.config import settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_admin_user(db: Session) -> User:
    """
    Crea un usuario administrador por defecto si no existe.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        User: El usuario administrador creado o existente
    """
    # Usar valores de configuración
    username = settings.DEFAULT_ADMIN_USERNAME
    email = settings.DEFAULT_ADMIN_EMAIL
    password = settings.DEFAULT_ADMIN_PASSWORD
    
    # Verificar si ya existe un usuario administrador
    admin = db.query(User).filter(User.username == username).first()
    
    if admin:
        logger.info(f"El usuario administrador '{username}' ya existe")
        return admin
    
    # Crear el usuario administrador
    admin_user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        full_name="Administrador",
        role=UserRole.ADMIN,
        is_superuser=True,
        is_verified=True,
        is_active=True
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    logger.info("Usuario administrador creado exitosamente")
    return admin_user

if __name__ == "__main__":
    db = SessionLocal()
    try:
        admin = init_admin_user(db)
        print(f"Usuario administrador creado/obtenido: {admin.username} ({admin.email})")
    except Exception as e:
        logger.error(f"Error al crear el usuario administrador: {e}")
        sys.exit(1)
    finally:
        db.close()
