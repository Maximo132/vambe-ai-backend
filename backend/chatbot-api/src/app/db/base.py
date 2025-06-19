"""
Módulo base para la configuración de la base de datos.

Este módulo proporciona la configuración base para SQLAlchemy,
incluyendo la clase Base para los modelos y la configuración de la conexión.
"""
import os
from typing import Generator, AsyncGenerator
from urllib.parse import urlparse, ParseResult
import logging

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from ..core.config import settings

# Configuración de logging
logger = logging.getLogger(__name__)

# Crear la clase base para los modelos
Base = declarative_base()

class Database:
    """Clase para gestionar la conexión a la base de datos."""
    
    def __init__(self):
        """Inicializa la conexión a la base de datos."""
        self.sync_engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        
        # Configurar motores
        self._setup_engines()
    
    def _setup_engines(self) -> None:
        """Configura los motores de base de datos síncrono y asíncrono."""
        # Configurar motor síncrono
        self.sync_engine = self._create_sync_engine()
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.sync_engine,
            class_=Session,
            expire_on_commit=False
        )
        
        # Configurar motor asíncrono
        self.async_engine = self._create_async_engine()
        self.AsyncSessionLocal = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    def _create_sync_engine(self):
        """Crea el motor de base de datos síncrono."""
        logger.info(f"Configurando motor de base de datos síncrono")
        return self._create_engine(settings.DATABASE_URL, is_async=False)
    
    def _create_async_engine(self):
        """Crea el motor de base de datos asíncrono."""
        logger.info(f"Configurando motor de base de datos asíncrono")
        return self._create_engine(settings.ASYNC_DATABASE_URL, is_async=True)
    
    def _create_engine(self, database_url: str, is_async: bool = False):
        """
        Crea un motor de base de datos.
        
        Args:
            database_url: URL de conexión a la base de datos
            is_async: Si es True, crea un motor asíncrono
            
        Returns:
            Motor de base de datos configurado
        """
        from sqlalchemy import create_engine
        from sqlalchemy.ext.asyncio import create_async_engine
        
        engine_args = {
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "pool_size": 5,
            "max_overflow": 10,
            "echo": settings.DEBUG,
            "future": True,
            "poolclass": QueuePool
        }
        
        if is_async:
            return create_async_engine(database_url, **engine_args)
        return create_engine(database_url, **engine_args)
    
    def get_sync_session(self) -> Generator[Session, None, None]:
        """Obtiene una sesión de base de datos síncrona."""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Obtiene una sesión de base de datos asíncrona."""
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    def get_engine(self, is_async: bool = False):
        """
        Obtiene el motor de base de datos.
        
        Args:
            is_async: Si es True, devuelve el motor asíncrono
            
        Returns:
            Motor de base de datos
        """
        return self.async_engine if is_async else self.sync_engine
    
    @staticmethod
    def obfuscate_url(url: str) -> str:
        """
        Ofusca las credenciales en una URL para logging.
        
        Args:
            url: URL a ofuscar
            
        Returns:
            URL con credenciales ofuscadas
        """
        parsed = urlparse(url)
        if parsed.password:
            netloc = f"{parsed.username}:*****@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            parsed = ParseResult(
                parsed.scheme, netloc, parsed.path,
                parsed.params, parsed.query, parsed.fragment
            )
        return parsed.geturl()

# Crear instancia de la base de datos
database = Database()

# Atajos para facilitar el acceso
get_db = database.get_sync_session
get_async_db = database.get_async_session
engine = database.sync_engine
async_engine = database.async_engine
SessionLocal = database.SessionLocal
AsyncSessionLocal = database.AsyncSessionLocal

# Importar modelos para que sean detectados por Alembic
from app.models import *  # noqa
