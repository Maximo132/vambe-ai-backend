"""
Script de inicialización de la base de datos.

Este script se encarga de crear las tablas necesarias en la base de datos
y realizar cualquier otra tarea de inicialización requerida.
"""
import asyncio
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .base import Base, database
from .session import async_engine, engine, async_session, SessionLocal, init_db
from ..core.config import settings

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_tables() -> None:
    """Crea todas las tablas en la base de datos."""
    logger.info("Creando tablas en la base de datos...")
    
    # Importar modelos para que sean detectados por SQLAlchemy
    from app.models.conversation import Conversation
    from app.models.message import Message
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Tablas creadas exitosamente")

async def drop_tables() -> None:
    """Elimina todas las tablas de la base de datos."""
    logger.warning("Eliminando todas las tablas de la base de datos...")
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.info("Todas las tablas han sido eliminadas")

async def check_db_connection() -> bool:
    """
    Verifica la conexión a la base de datos.
    
    Returns:
        bool: True si la conexión es exitosa, False en caso contrario
    """
    try:
        # Verificar conexión síncrona
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        
        # Verificar conexión asíncrona
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        logger.info("Conexión a la base de datos verificada correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos: {e}")
        return False

async def init() -> None:
    """
    Inicializa la base de datos.
    
    Este es el punto de entrada principal para la inicialización de la base de datos.
    """
    logger.info("Inicializando base de datos...")
    
    # Verificar conexión
    if not await check_db_connection():
        logger.error("No se pudo establecer conexión con la base de datos")
        return
    
    # Crear tablas
    await create_tables()
    
    logger.info("Inicialización de la base de datos completada")

if __name__ == "__main__":
    # Ejecutar la inicialización
    asyncio.run(init())
