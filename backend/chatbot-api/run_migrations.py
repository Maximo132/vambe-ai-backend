import os
import sys
import logging
import traceback
from pathlib import Path

# Configurar logging con formato detallado
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
    src_path = str(base_dir / "src")
    
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    # Configurar la URL de la base de datos
    db_url = "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db"
    os.environ["DATABASE_URL"] = db_url
    
    logger.info(f"Directorio base: {base_dir}")
    logger.info(f"Directorio src: {src_path}")
    logger.info(f"URL de la base de datos: {db_url}")
    
    # Verificar que el directorio de migraciones existe
    migrations_dir = base_dir / "migrations"
    if not migrations_dir.exists():
        logger.info("Creando directorio de migraciones...")
        migrations_dir.mkdir()
    
    return base_dir, src_path, db_url

def run_migrations():
    """Ejecuta las migraciones de Alembic."""
    try:
        logger.info("Iniciando configuración del entorno...")
        base_dir, src_path, db_url = setup_environment()
        
        # Verificar que el directorio de migraciones existe
        if not (base_dir / "migrations").exists():
            logger.error("El directorio de migraciones no existe. Ejecuta 'alembic init migrations' primero.")
            return False
            
        # Verificar que el archivo env.py existe
        env_py = base_dir / "migrations" / "env.py"
        if not env_py.exists():
            logger.error(f"No se encontró el archivo {env_py}. Asegúrate de haber inicializado Alembic correctamente.")
            return False
            
        logger.info("Configuración del entorno completada")
        
        # Importar después de configurar el path
        logger.debug("Importando módulos de Alembic...")
        from alembic.config import Config
        from alembic import command
        
        # Configuración de Alembic
        logger.debug("Configurando Alembic...")
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(base_dir / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        # Mostrar configuración
        logger.debug(f"Configuración de Alembic: {dict(alembic_cfg.get_section('alembic'))}")
        
        # Verificar la conexión a la base de datos
        logger.info("Verificando conexión a la base de datos...")
        try:
            from sqlalchemy import create_engine
            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("✓ Conexión a la base de datos exitosa")
        except Exception as e:
            logger.error(f"✗ Error al conectar a la base de datos: {e}")
            return False
        
        # Crear una migración automática
        logger.info("\nCreando migración automática...")
        try:
            command.revision(
                config=alembic_cfg,
                autogenerate=True,
                message="Initial migration"
            )
            logger.info("✓ Migración creada exitosamente")
        except Exception as e:
            logger.error(f"✗ Error al crear la migración: {e}")
            logger.debug(traceback.format_exc())
            return False
        
        # Aplicar las migraciones
        logger.info("\nAplicando migraciones...")
        try:
            command.upgrade(alembic_cfg, "head")
            logger.info("✓ Migraciones aplicadas con éxito")
            return True
        except Exception as e:
            logger.error(f"✗ Error al aplicar migraciones: {e}")
            logger.debug(traceback.format_exc())
            return False
        
    except Exception as e:
        logger.critical(f"Error inesperado: {e}")
        logger.debug(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
