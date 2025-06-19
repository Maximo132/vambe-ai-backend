#!/usr/bin/env python
"""
Script para ejecutar migraciones de Alembic con mayor control.
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
        logging.FileHandler('migration.log')
    ]
)
logger = logging.getLogger(__name__)

def run_migration():
    """Ejecuta la migración de Alembic."""
    try:
        # Añadir el directorio src al path
        src_dir = str(Path(__file__).parent.absolute() / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        
        # Configurar la URL de la base de datos
        db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db")
        os.environ["DATABASE_URL"] = db_url
        
        # Importar la configuración de Alembic
        from alembic.config import Config
        from alembic import command
        
        # Configurar Alembic
        alembic_cfg = Config("alembic.ini")
        
        # Generar la migración
        logger.info("Generando migración...")
        command.revision(
            config=alembic_cfg,
            autogenerate=True,
            message="Initial migration"
        )
        
        # Aplicar la migración
        logger.info("Aplicando migración...")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("¡Migración completada exitosamente!")
        return True
        
    except Exception as e:
        logger.error(f"Error al ejecutar la migración: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Iniciando migración de la base de datos...")
    success = run_migration()
    sys.exit(0 if success else 1)
