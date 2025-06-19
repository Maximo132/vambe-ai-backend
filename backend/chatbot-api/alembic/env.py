"""
Entorno de ejecución de migraciones de Alembic.

Este archivo configura el entorno para ejecutar migraciones de base de datos
usando Alembic con soporte para SQLAlchemy asíncrono.
"""
import asyncio
import logging
import os
import sys
from logging.config import fileConfig
from typing import Callable, Generator, Optional

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from dotenv import load_dotenv

# Añadir el directorio src al path para poder importar los modelos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar variables de entorno
load_dotenv()

# Importar los modelos para que Alembic los detecte
from app.models import Base
from app.core.config import settings

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alembic")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Ejecuta las migraciones en el contexto de una conexión dada.
    
    Args:
        connection: Conexión a la base de datos
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Para operaciones normales (síncronas)
    connectable = Engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
        future=True
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    # Para operaciones asíncronas (si es necesario)
    # async_connectable = create_async_engine(
    #     settings.ASYNC_DATABASE_URL,
    #     pool_pre_ping=True,
    #     pool_recycle=3600,
    #     pool_size=5,
    #     max_overflow=10,
    #     future=True
    # )
    #
    # async with async_connectable.connect() as connection:
    #     await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Usar asyncio.run() para ejecutar la función asíncrona
    # desde un contexto síncrono
    asyncio.run(run_migrations_online())
