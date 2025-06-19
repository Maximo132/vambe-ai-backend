
import os
import sys
import logging
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('alembic.log')
    ]
)

# Configurar el logger de SQLAlchemy
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
logger = logging.getLogger('alembic')

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Añadir el directorio src al path
current_dir = Path(__file__).parent.absolute()
root_dir = current_dir.parent
src_dir = root_dir / "src"

# Asegurarse de que el directorio src esté en el path
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Importar después de ajustar el path
try:
    logger.info(f"Intentando importar desde: {src_dir}")
    logger.info(f"Python path: {sys.path}")
    
    # Importar la configuración de la base de datos
    from app.db.base import Base, database
    
    # Importar los modelos para que sean detectados por Alembic
    from app import models  # Importar modelos para que se registren con Base
    
    # Configurar la URL de la base de datos
    db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db")
    database.set_url(db_url)
    
    logger.info(f"Base metadata: {Base.metadata}")
    target_metadata = Base.metadata
    
except ImportError as e:
    logger.error(f"Error al importar módulos: {e}", exc_info=True)
    raise

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = database.engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
