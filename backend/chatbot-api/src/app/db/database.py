"""
Módulo para la gestión de la base de datos.

Este módulo proporciona una conexión a la base de datos y una sesión de base de datos
para interactuar con la base de datos PostgreSQL.
"""
import logging
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from ..core.config import settings

# Configurar logging
logger = logging.getLogger(__name__)

# Crear el motor de la base de datos
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
    pool_timeout=30,
    echo=settings.DEBUG
)

# Crear una fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Proveedor de dependencias para obtener una sesión de base de datos.
    
    Yields:
        Session: Una sesión de base de datos.
        
    Example:
        >>> def some_endpoint(db: Session = Depends(get_db)):
        ...     # Usar la sesión de la base de datos
        ...     users = db.query(User).all()
        ...     return users
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos: {e}")
        db.rollback()
        raise
    finally:
        db.close()

async def init_db() -> None:
    """
    Inicializa la base de datos creando las tablas si no existen.
    
    Esta función debe llamarse al iniciar la aplicación.
    """
    try:
        from . import models  # Importar modelos para que se registren con Base
        
        logger.info("Creando tablas en la base de datos...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas creadas exitosamente")
        
        # Inicializar datos por defecto
        await init_default_data()
        
    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
        raise

async def close_db() -> None:
    """
    Cierra las conexiones a la base de datos.
    
    Esta función debe llamarse al cerrar la aplicación.
    """
    logger.info("Cerrando conexiones a la base de datos...")
    engine.dispose()
    logger.info("Conexiones a la base de datos cerradas")

async def init_default_data() -> None:
    """
    Inicializa la base de datos con datos por defecto.
    
    Esta función crea usuarios, roles y otros datos iniciales necesarios
    para el funcionamiento de la aplicación.
    """
    from sqlalchemy.orm import Session
    from ..models.user import User, UserRole
    from ..schemas.user import UserCreate
    from ..core.security import get_password_hash
    
    db = SessionLocal()
    try:
        # Verificar si ya existen usuarios
        if db.query(User).first() is not None:
            logger.info("La base de datos ya contiene datos, omitiendo inicialización")
            return
            
        logger.info("Inicializando datos por defecto...")
        
        # Crear roles por defecto
        roles = ["admin", "user", "guest"]
        for role_name in roles:
            if not db.query(UserRole).filter(UserRole.name == role_name).first():
                db.add(UserRole(name=role_name))
        
        db.commit()
        
        # Crear usuario administrador por defecto
        admin_role = db.query(UserRole).filter(UserRole.name == "admin").first()
        if admin_role and not db.query(User).filter(User.email == "admin@vambe.ai").first():
            admin_user = User(
                email="admin@vambe.ai",
                hashed_password=get_password_hash("admin123"),
                full_name="Administrador",
                is_active=True,
                is_superuser=True,
                role_id=admin_role.id
            )
            db.add(admin_user)
            db.commit()
            logger.info("Usuario administrador creado: admin@vambe.ai / admin123")
            
    except Exception as e:
        logger.error(f"Error al inicializar datos por defecto: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# Exportar la sesión para uso en otros módulos
Session = SessionLocal
