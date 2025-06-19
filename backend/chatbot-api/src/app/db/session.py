"""
Módulo de configuración de sesiones de base de datos.

Este módulo proporciona la configuración de las sesiones de base de datos
tanto síncronas como asíncronas para su uso en la aplicación.
"""
from typing import AsyncGenerator, Generator, TypeVar, Type, Any
from contextlib import asynccontextmanager, contextmanager
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session, declarative_base
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declared_attr

from ..core.config import settings

# Configuración de logging
logger = logging.getLogger(__name__)

# Tipo genérico para las sesiones
T = TypeVar('T', AsyncSession, Session)

# Configuración de motores
engine = None
async_engine = None
SessionLocal = None
AsyncSessionLocal = None
Base = declarative_base()

def init_db() -> None:
    """
    Inicializa los motores y las fábricas de sesiones.
    Debe llamarse al inicio de la aplicación.
    """
    global engine, async_engine, SessionLocal, AsyncSessionLocal
    
    # Configuración del motor síncrono
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
        echo=settings.DEBUG,
        future=True
    )
    
    # Configuración del motor asíncrono
    async_engine = create_async_engine(
        settings.ASYNC_DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
        echo=settings.DEBUG,
        future=True
    )
    
    # Configuración de la fábrica de sesiones síncronas
    SessionLocal = scoped_session(
        sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            class_=Session,
            expire_on_commit=False
        )
    )
    
    # Configuración de la fábrica de sesiones asíncronas
    AsyncSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    logger.info("Motores y sesiones de base de datos inicializados correctamente")

def get_db() -> Generator[Session, None, None]:
    """
    Proveedor de dependencia para FastAPI (síncrono).
    
    Yields:
        Session: Sesión de base de datos síncrona
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Proveedor de dependencia para FastAPI (asíncrono).
    
    Yields:
        AsyncSession: Sesión de base de datos asíncrona
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error en la sesión de base de datos: {e}")
            raise
        finally:
            await session.close()

@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """
    Context manager para sesiones síncronas.
    
    Yields:
        Session: Sesión de base de datos síncrona
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager para sesiones asíncronas.
    
    Yields:
        AsyncSession: Sesión de base de datos asíncrona
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error en la sesión de base de datos: {e}")
            raise
        finally:
            await session.close()

# Inicializar la base de datos al importar el módulo
init_db()

# Importar modelos para que sean detectados por SQLAlchemy
# Debe ir después de la definición de Base
from app.models import *  # noqa
