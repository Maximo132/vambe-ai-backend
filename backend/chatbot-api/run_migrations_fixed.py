#!/usr/bin/env python
"""
Script para ejecutar migraciones de Alembic de manera controlada.
"""
import os
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('migrations.log')
    ]
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Configura el entorno para las migraciones."""
    # Añadir el directorio src al path
    base_dir = Path(__file__).parent.absolute()
    src_dir = base_dir / "src"
    
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    
    # Configurar la URL de la base de datos
    os.environ["DATABASE_URL"] = "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db"
    
    logger.info(f"Directorio base: {base_dir}")
    logger.info(f"Directorio src: {src_dir}")
    
    return base_dir, src_dir

def run_migrations():
    """Ejecuta las migraciones de Alembic."""
    try:
        logger.info("Configurando entorno...")
        base_dir, src_dir = setup_environment()
        
        # Verificar que el directorio de migraciones existe
        migrations_dir = base_dir / "migrations"
        if not migrations_dir.exists():
            logger.error("El directorio de migraciones no existe. Ejecuta 'alembic init migrations' primero.")
            return False
        
        # Verificar que el archivo env.py existe
        env_py = migrations_dir / "env.py"
        if not env_py.exists():
            logger.error(f"No se encontró el archivo {env_py}. Asegúrate de haber inicializado Alembic correctamente.")
            return False
        
        # Importar Alembic después de configurar el path
        from alembic.config import Config
        from alembic import command
        
        # Configuración de Alembic
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(migrations_dir))
        alembic_cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
        
        # Mostrar configuración
        logger.info("Configuración de Alembic:")
        for key, value in alembic_cfg.get_section("alembic").items():
            logger.info(f"  {key} = {value}")
        
        # Verificar la conexión a la base de datos
        logger.info("Verificando conexión a la base de datos...")
        from sqlalchemy import create_engine
        engine = create_engine(os.environ["DATABASE_URL"])
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info(f"✓ Conexión exitosa: {result.scalar() == 1}")
        
        # Crear una migración automática
        logger.info("\nCreando migración automática...")
        command.revision(
            config=alembic_cfg,
            autogenerate=True,
            message="Initial migration"
        )
        
        # Aplicar las migraciones
        logger.info("\nAplicando migraciones...")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("\n¡Migraciones aplicadas con éxito!")
        return True
        
    except Exception as e:
        logger.error(f"Error durante las migraciones: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
