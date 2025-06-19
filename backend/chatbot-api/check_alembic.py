#!/usr/bin/env python
"""
Script para verificar el estado de Alembic y la base de datos.
"""
import os
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('check_alembic.log')
    ]
)
logger = logging.getLogger(__name__)

def check_database():
    """Verifica la conexión a la base de datos y las tablas."""
    try:
        # Añadir el directorio src al path
        src_dir = str(Path(__file__).parent.absolute() / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        
        # Importar la configuración de la base de datos
        from app.db.base import database
        
        # Verificar conexión
        with database.SessionLocal() as session:
            result = session.execute("SELECT version()")
            version = result.scalar()
            logger.info(f"Conectado a PostgreSQL: {version}")
            
            # Verificar tablas
            result = session.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Tablas en la base de datos: {tables}")
            
            # Verificar tabla alembic_version
            if 'alembic_version' in tables:
                result = session.execute("SELECT version_num FROM alembic_version")
                version = result.scalar()
                logger.info(f"Versión de Alembic: {version}")
            else:
                logger.warning("La tabla alembic_version no existe")
        
        return True
        
    except Exception as e:
        logger.error(f"Error al verificar la base de datos: {e}", exc_info=True)
        return False

def check_alembic():
    """Verifica la configuración de Alembic."""
    try:
        # Verificar si existe el directorio de migraciones
        migrations_dir = Path("migrations")
        if not migrations_dir.exists():
            logger.error("No se encontró el directorio de migraciones")
            return False
        
        # Verificar si existe el archivo env.py
        env_py = migrations_dir / "env.py"
        if not env_py.exists():
            logger.error("No se encontró el archivo env.py")
            return False
        
        # Verificar si existe el directorio de versiones
        versions_dir = migrations_dir / "versions"
        if not versions_dir.exists():
            logger.error("No se encontró el directorio de versiones")
            return False
        
        logger.info("Configuración de Alembic verificada correctamente")
        return True
        
    except Exception as e:
        logger.error(f"Error al verificar Alembic: {e}", exc_info=True)
        return False

def main():
    """Función principal."""
    logger.info("Iniciando verificación...")
    
    # Verificar la base de datos
    if not check_database():
        logger.error("Error al verificar la base de datos")
        return False
    
    # Verificar Alembic
    if not check_alembic():
        logger.error("Error al verificar Alembic")
        return False
    
    logger.info("¡Verificación completada exitosamente!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
