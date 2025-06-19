#!/usr/bin/env python
"""
Script para inicializar la base de datos y configurar Alembic.
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
        logging.FileHandler('init_database.log')
    ]
)
logger = logging.getLogger(__name__)

def setup_database():
    """Configura la base de datos y crea las tablas."""
    try:
        # Añadir el directorio src al path
        src_dir = str(Path(__file__).parent.absolute() / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        
        # Configurar la URL de la base de datos
        db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db")
        os.environ["DATABASE_URL"] = db_url
        
        # Importar la configuración de la base de datos
        from app.db.base import Base, database
        
        # Configurar la base de datos
        database.set_url(db_url)
        
        # Crear todas las tablas
        logger.info("Creando tablas en la base de datos...")
        Base.metadata.create_all(bind=database.engine)
        
        logger.info("¡Base de datos inicializada correctamente!")
        return True
        
    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {e}", exc_info=True)
        return False

def setup_alembic():
    """Configura Alembic para migraciones."""
    try:
        # Asegurarse de que el directorio de migraciones existe
        migrations_dir = Path("migrations")
        if not migrations_dir.exists():
            logger.info("Creando directorio de migraciones...")
            migrations_dir.mkdir()
            
        # Crear archivo alembic.ini si no existe
        alembic_ini = Path("alembic.ini")
        if not alembic_ini.exists():
            logger.info("Creando archivo alembic.ini...")
            with open(alembic_ini, 'w') as f:
                f.write('''[alembic]
script_location = migrations
sqlalchemy.url = postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console,file

[formatters]
keys = generic

[logger_root]
level = INFO
handlers = console,file
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[handler_file]
class = FileHandler
args = ('alembic.log', 'a')
level = DEBUG
formatter = generic

[formatter_generic]
format = %(asctime)s [%(levelname)s] %(name)s: %(message)s
datefmt = %Y-%m-%d %H:%M:%S
''')
        
        # Crear directorio de versiones si no existe
        versions_dir = migrations_dir / "versions"
        if not versions_dir.exists():
            logger.info("Creando directorio de versiones...")
            versions_dir.mkdir()
            
            # Crear archivo __init__.py en el directorio de versiones
            (versions_dir / "__init__.py").touch()
        
        # Crear archivo env.py si no existe
        env_py = migrations_dir / "env.py"
        if not env_py.exists():
            logger.info("Creando archivo env.py...")
            with open(env_py, 'w') as f:
                f.write('''import os
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
''')
        
        logger.info("Configuración de Alembic completada")
        return True
        
    except Exception as e:
        logger.error(f"Error al configurar Alembic: {e}", exc_info=True)
        return False

def main():
    """Función principal."""
    logger.info("Iniciando configuración de la base de datos...")
    
    # Configurar la base de datos
    if not setup_database():
        logger.error("Error al configurar la base de datos")
        return False
    
    # Configurar Alembic
    if not setup_alembic():
        logger.error("Error al configurar Alembic")
        return False
    
    logger.info("¡Configuración completada exitosamente!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
