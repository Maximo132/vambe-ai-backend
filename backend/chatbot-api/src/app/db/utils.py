"""
Utilidades para la base de datos.

Este módulo proporciona funciones de utilidad para trabajar con la base de datos,
incluyendo la gestión de sesiones, conexiones y transacciones.
"""
from typing import AsyncGenerator, Callable, TypeVar, Any
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session as SyncSession
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging

from ..core.config import settings

# Configuración de logging
logger = logging.getLogger(__name__)

# Tipo genérico para las sesiones
T = TypeVar('T', AsyncSession, SyncSession)

# Configuración de conexión síncrona
sync_engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,
    future=True
)

# Configuración de conexión asíncrona
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,
    future=True
)

# Fábricas de sesiones
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
    class_=SyncSession,
    expire_on_commit=False
)

AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Context manager para sesiones síncronas
def get_sync_db() -> SyncSession:
    """
    Obtiene una sesión de base de datos síncrona.
    
    Returns:
        SyncSession: Sesión de base de datos síncrona
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Context manager para sesiones asíncronas
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Obtiene una sesión de base de datos asíncrona.
    
    Yields:
        AsyncSession: Sesión de base de datos asíncrona
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Error en la sesión de base de datos: {e}")
            raise
        finally:
            await session.close()

@asynccontextmanager
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager para manejar sesiones de base de datos asíncronas.
    
    Yields:
        AsyncSession: Sesión de base de datos asíncrona
    """
    async with get_async_db() as session:
        yield session

async def init_db() -> None:
    """
    Inicializa la base de datos creando todas las tablas.
    """
    from ..models.base import Base
    
    logger.info("Creando tablas de la base de datos...")
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Tablas creadas exitosamente")

async def check_db_connection() -> bool:
    """
    Verifica la conexión a la base de datos.
    
    Returns:
        bool: True si la conexión es exitosa, False en caso contrario
    """
    try:
        # Para conexión síncrona
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # Para conexión asíncrona
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        return True
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos: {e}")
        return False

def get_session_factory(is_async: bool = True) -> Callable[..., Any]:
    """
    Obtiene la fábrica de sesiones apropiada según el modo.
    
    Args:
        is_async: Si es True, devuelve la fábrica de sesiones asíncronas
        
    Returns:
        Callable: Función que devuelve una sesión de base de datos
    """
    return get_async_db if is_async else get_sync_db

def get_engine(is_async: bool = True) -> Any:
    """
    Obtiene el motor de base de datos apropiado según el modo.
    
    Args:
        is_async: Si es True, devuelve el motor asíncrono
        
    Returns:
        Engine: Motor de base de datos
    """
    return async_engine if is_async else sync_engine
