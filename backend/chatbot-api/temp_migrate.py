"""
Script para ejecutar migraciones de Alembic manualmente.
"""
import os
import sys
import logging
from alembic.config import Config
from alembic import command

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """Ejecuta las migraciones de Alembic."""
    try:
        # Configurar Alembic
        config = Config("alembic.ini")
        
        # Mostrar información de depuración
        logger.info("Iniciando migraciones...")
        logger.info(f"Directorio de trabajo: {os.getcwd()}")
        logger.info(f"Ruta de configuración: {os.path.abspath('alembic.ini')}")
        
        # Mostrar la configuración de la base de datos (sin contraseña)
        with open('alembic.ini', 'r') as f:
            logger.info("Contenido de alembic.ini:")
            for line in f:
                if 'sqlalchemy.url' in line and 'postgresql' in line:
                    # Ocultar la contraseña en los logs
                    safe_line = line.split('@')
                    if len(safe_line) > 1:
                        safe_line[0] = safe_line[0].split(':')[0] + ':***@'
                        logger.info(''.join(safe_line).strip())
                    else:
                        logger.info(line.strip())
                else:
                    logger.info(line.strip())
        
        # Verificar si la tabla de control de migraciones existe
        from sqlalchemy import create_engine, inspect
        from app.core.config import settings
        
        engine = create_engine(settings.DATABASE_URL)
        inspector = inspect(engine)
        
        if 'alembic_version' not in inspector.get_table_names():
            logger.info("La tabla de control de migraciones no existe. Creando...")
            command.stamp(config, "head")
        
        # Ejecutar migraciones
        logger.info("Ejecutando migraciones...")
        command.upgrade(config, "head")
        
        logger.info("Migraciones completadas exitosamente.")
        return True
    except Exception as e:
        logger.error(f"Error al ejecutar migraciones: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    # Asegurarse de que el directorio src esté en el path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Cargar variables de entorno
    from dotenv import load_dotenv
    load_dotenv()
    
    # Ejecutar migraciones
    success = run_migrations()
    sys.exit(0 if success else 1)
