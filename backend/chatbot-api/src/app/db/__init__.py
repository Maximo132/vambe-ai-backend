"""
Paquete de base de datos.

Este paquete proporciona toda la funcionalidad necesaria para interactuar con la base de datos,
incluyendo la configuración de conexiones, sesiones, modelos y utilidades.
"""
from .base import Base, database
from .session import (
    get_db,
    get_async_db,
    get_sync_session,
    get_async_session,
    SessionLocal,
    AsyncSessionLocal,
    engine,
    async_engine,
    Base as BaseModel,
    init_db as init_database
)
from .utils import (
    get_session_factory,
    get_engine,
    async_db_session,
    check_db_connection
)

# Inicializar la base de datos al importar el paqueto
init_database()

__all__ = [
    # Clases base
    'Base',
    'database',
    'BaseModel',
    
    # Sesiones
    'get_db',
    'get_async_db',
    'get_sync_session',
    'get_async_session',
    'SessionLocal',
    'AsyncSessionLocal',
    
    # Motores
    'engine',
    'async_engine',
    'get_engine',
    
    # Utilidades
    'get_session_factory',
    'async_db_session',
    'check_db_connection',
    'init_database'
]
