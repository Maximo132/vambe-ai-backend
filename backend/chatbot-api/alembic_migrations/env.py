"""
Entorno de ejecución de migraciones de Alembic para Vambe.ai Chatbot API.
"""
import asyncio
import logging
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool, text
from sqlalchemy.engine import Connection
from dotenv import load_dotenv

# Asegurarse de que el directorio src esté en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alembic")

# Configuración de Alembic
config = context.config

# Interpretar el archivo de configuración para logging de Python
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importar configuración de la aplicación
from app.core.config import settings

# Importar los modelos para que Alembic los detecte
# Importar solo después de configurar el logging
from app.models.base import Base
from app.models.user import User, UserRole
from app.models.conversation import Conversation, Message, ConversationStatus
from app.models.document import Document
from app.models.login_history import LoginHistory
from app.models.auth_token import AuthToken

# Configurar metadata para Alembic
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline'."""
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
    """Ejecuta las migraciones en el contexto de una conexión dada."""
    # Verificar si la extensión uuid-ossp está habilitada
    try:
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        connection.commit()
    except Exception as e:
        logger.warning(f"No se pudo crear la extensión uuid-ossp: {e}")
    
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        version_table_schema=target_metadata.schema,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online'."""
    # Usar la URL de la base de datos de las configuraciones
    database_url = settings.DATABASE_URL
    logger.info(f"Conectando a la base de datos: {database_url}")
    
    connectable = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
        future=True,
        echo=True  # Habilita logging de SQL
    )

    with connectable.connect() as connection:
        logger.info("Conexión a la base de datos establecida")
        do_run_migrations(connection)

# Determinar el modo de ejecución
if context.is_offline_mode():
    logger.info("Ejecutando migraciones en modo OFFLINE")
    run_migrations_offline()
else:
    logger.info("Ejecutando migraciones en modo ONLINE")
    run_migrations_online()
