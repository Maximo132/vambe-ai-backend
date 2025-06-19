#!/usr/bin/env python
"""
Script para inicializar Alembic y generar migraciones iniciales.
"""
import os
import sys
import logging
from pathlib import Path
from alembic.config import Config
from alembic import command

def main():
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('alembic_init.log')
        ]
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Configurar la ruta base
        base_dir = Path(__file__).parent.absolute()
        
        # Configurar la URL de la base de datos
        db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db")
        
        # Configurar Alembic
        alembic_cfg = Config(os.path.join(base_dir, "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        # Crear migración inicial
        logger.info("Generando migración inicial...")
        command.revision(
            config=alembic_cfg,
            autogenerate=True,
            message="Initial migration"
        )
        
        # Aplicar migración
        logger.info("Aplicando migración...")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("¡Migración completada exitosamente!")
        return True
        
    except Exception as e:
        logger.error(f"Error al inicializar Alembic: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
