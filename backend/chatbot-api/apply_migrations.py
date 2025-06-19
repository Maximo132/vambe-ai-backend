#!/usr/bin/env python
"""
Script para aplicar migraciones de Alembic.
"""
import os
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
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
    
    try:
        # Importar Alembic
        from alembic.config import Config
        from alembic import command
        
        # Configuración de Alembic
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "migrations")
        alembic_cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
        
        # Aplicar migraciones
        logger.info("Aplicando migraciones...")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("¡Migraciones aplicadas con éxito!")
        return True
        
    except Exception as e:
        logger.error(f"Error al aplicar migraciones: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
