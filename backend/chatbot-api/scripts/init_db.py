"""
Script para inicializar la base de datos y aplicar migraciones.

Este script se encarga de:
1. Configurar las rutas de importación
2. Inicializar la base de datos
3. Aplicar migraciones con Alembic
4. Crear datos iniciales si es necesario
"""
import sys
import os
import logging
from pathlib import Path
from typing import Optional

def setup_paths() -> None:
    """
    Configura las rutas necesarias para las importaciones.
    
    Asegura que los módulos de la aplicación puedan ser importados correctamente
    independientemente del directorio desde donde se ejecute el script.
    """
    # Obtener la ruta raíz del proyecto (directorio que contiene src/ y scripts/)
    project_root = Path(__file__).parent.parent
    src_path = project_root / 'src'
    
    # Añadir src/ al path de Python si no está ya incluido
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
        
    # Configurar logging básico
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Configurar nivel de logging para SQLAlchemy
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    sys.path.insert(0, str(src_path))
    return project_root, src_path

def import_required_modules():
    """
    Importa los módulos necesarios para la inicialización.
    
    Returns:
        tuple: Tupla con los módulos importados
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Importaciones dentro de la función para evitar problemas de importación circular
        from alembic.config import Config
        from alembic import command
        from sqlalchemy import create_engine, text
        
        # Importar configuración de la aplicación
        from app.core.config import settings
        from app.db.base import Base, database
        from app.db.session import engine, SessionLocal
        
        logger.info("Módulos requeridos importados correctamente")
        return {
            'Config': Config,
            'command': command,
            'create_engine': create_engine,
            'text': text,
            'settings': settings,
            'Base': Base,
            'database': database,
            'engine': engine,
            'SessionLocal': SessionLocal
        }
    except ImportError as e:
        logger.error(f"Error al importar módulos requeridos: {e}")
        logger.exception("Detalles completos del error:")
        sys.exit(1)

def run_migrations(modules: dict) -> None:
    """
    Ejecuta las migraciones de Alembic.
    
    Args:
        modules: Diccionario con los módulos importados
    """
    logger = logging.getLogger(__name__)
    Config = modules['Config']
    command = modules['command']
    engine = modules['engine']
    
    # Ruta al directorio de migraciones
    migrations_dir = Path(__file__).parent.parent / 'alembic'
    
    # Configuración de Alembic
    alembic_cfg = Config()
    alembic_cfg.set_main_option('script_location', str(migrations_dir))
    alembic_cfg.set_main_option('sqlalchemy.url', str(modules['settings'].DATABASE_URL))
    
    try:
        # Asegurarse de que todos los modelos estén cargados
        from app.models import *  # noqa
        
        # Verificar la conexión a la base de datos
        logger.info("Verificando conexión a la base de datos...")
        with engine.connect() as conn:
            conn.execute(modules['text']("SELECT 1"))
        
        # Ejecutar migraciones
        logger.info("Ejecutando migraciones...")
        command.upgrade(alembic_cfg, "head")
        
        # Verificar el estado de las migraciones
        logger.info("Verificando estado de migraciones...")
        command.check(alembic_cfg)
        
        logger.info("Migraciones aplicadas exitosamente.")
        return True
    except Exception as e:
        logger.error(f"Error al ejecutar migraciones: {e}")
        logger.exception("Detalles completos del error:")
        return False

def create_initial_data(db_session):
    """
    Crea datos iniciales en la base de datos.
    
    Args:
        db_session: Sesión de base de datos
    """
    logger = logging.getLogger(__name__)
    logger.info("Verificando datos iniciales...")
    
    try:
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash
        from app.core.config import settings
        
        # Verificar si ya existe el usuario administrador por defecto
        admin = db_session.query(User).filter(
            User.username == settings.DEFAULT_ADMIN_USERNAME
        ).first()
        
        if not admin and settings.CREATE_DEFAULT_ADMIN:
            logger.info(f"Creando usuario administrador por defecto: {settings.DEFAULT_ADMIN_USERNAME}")
            
            admin_user = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                full_name="Administrador",
                role=UserRole.ADMIN,
                is_superuser=True,
                is_verified=True,
                is_active=True
            )
            
            db_session.add(admin_user)
            db_session.commit()
            logger.info(f"Usuario administrador '{settings.DEFAULT_ADMIN_USERNAME}' creado exitosamente")
            
            # Mostrar credenciales (solo en desarrollo)
            if settings.DEBUG:
                logger.info("=== Credenciales de administrador ===")
                logger.info(f"Usuario: {settings.DEFAULT_ADMIN_USERNAME}")
                logger.info(f"Contraseña: {settings.DEFAULT_ADMIN_PASSWORD}")
                logger.info("===================================")
        elif admin:
            logger.info(f"El usuario administrador '{settings.DEFAULT_ADMIN_USERNAME}' ya existe")
            logger.info("Usuario administrador creado exitosamente.")
        else:
            logger.info("El usuario administrador ya existe.")
            
    except Exception as e:
        logger.error(f"Error al crear datos iniciales: {e}")
        logger.exception("Detalles completos del error:")
        db_session.rollback()
        raise

def main() -> int:
    """
    Función principal para la inicialización de la base de datos.
    
    Returns:
        int: Código de salida (0 para éxito, 1 para error)
    """
    # Configurar logging
    logger = logging.getLogger(__name__)
    
    try:
        # Configurar rutas
        setup_paths()
        logger.info("Rutas configuradas correctamente.")
        
        # Importar módulos necesarios
        modules = import_required_modules()
        settings = modules['settings']
        SessionLocal = modules['SessionLocal']
        
        # Verificar si la URL de la base de datos está configurada
        if not settings.DATABASE_URL:
            logger.error("Error: DATABASE_URL no está configurada en las variables de entorno.")
            return 1
        
        logger.info(f"Inicializando base de datos: {settings.DATABASE_URL}")
        
        # Ejecutar migraciones
        if not run_migrations(modules):
            return 1
        
        # Crear datos iniciales
        logger.info("Creando datos iniciales...")
        db = SessionLocal()
        try:
            create_initial_data(db)
            logger.info("Datos iniciales creados exitosamente.")
        except Exception as e:
            logger.error(f"Error al crear datos iniciales: {e}")
            return 1
        finally:
            db.close()
        
        logger.info("Base de datos inicializada exitosamente.")
        return 0
        
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        logger.exception("Detalles completos del error:")
        return 1

if __name__ == "__main__":
    sys.exit(main())
