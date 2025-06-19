#!/usr/bin/env python
"""
Script simplificado para ejecutar migraciones de Alembic.
"""
import os
import sys
import logging
from pathlib import Path

# Configurar logging básico
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Añadir el directorio src al path
    src_dir = str(Path(__file__).parent.absolute() / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    
    # Configurar la URL de la base de datos
    os.environ["DATABASE_URL"] = "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db"
    
    logger.info(f"Python path: {sys.path}")
    logger.info(f"Database URL: {os.environ['DATABASE_URL']}")
    
    try:
        # Intentar importar los módulos necesarios
        logger.info("Intentando importar módulos...")
        from app.db.base import Base, database
        from app import models  # Para registrar los modelos
        
        logger.info(f"Base metadata: {Base.metadata}")
        
        # Verificar la conexión a la base de datos
        logger.info("Verificando conexión a la base de datos...")
        engine = database.get_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info(f"Conexión exitosa: {result.scalar() == 1}")
        
        # Importar y configurar Alembic
        from alembic.config import Config
        from alembic import command
        
        # Configuración de Alembic
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "migrations")
        alembic_cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
        
        # Crear migración
        logger.info("\nCreando migración...")
        command.revision(
            config=alembic_cfg,
            autogenerate=True,
            message="Initial migration"
        )
        
        # Aplicar migraciones
        logger.info("\nAplicando migraciones...")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("\n¡Migraciones aplicadas con éxito!")
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
