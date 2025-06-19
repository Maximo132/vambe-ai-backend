from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, scoped_session, Session, declarative_base, sessionmaker
from sqlalchemy.ext.declarative import declared_attr
from ..core.config import settings

# Configuración de conexión síncrona (para operaciones que requieren SQLAlchemy ORM síncrono)
SYNC_DATABASE_URL = settings.DATABASE_URL

# Configuración de conexión asíncrona (para operaciones asíncronas)
ASYNC_DATABASE_URL = settings.ASYNC_DATABASE_URL

# Motor síncrono para operaciones que no soportan asincronía
engine = create_engine(
    SYNC_DATABASE_URL,
    pool_pre_ping=True,  # Verifica que la conexión esté activa antes de usarla
    pool_recycle=3600,   # Recicla conexiones después de 1 hora
    pool_size=5,         # Número de conexiones a mantener en el pool
    max_overflow=10,     # Número máximo de conexiones adicionales a crear
    echo=settings.DEBUG, # Muestra las consultas SQL en consola
    future=True          # Habilita el comportamiento de SQLAlchemy 2.0
)

# Motor asíncrono para operaciones asíncronas
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,
    future=True
)

# Fábrica de sesiones síncronas
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Evita que las instancias se expiren después del commit
    class_=Session
)

# Fábrica de sesiones asíncronas
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# Base para los modelos
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Proveedor de dependencia para FastAPI (síncrono).
    Crea una nueva sesión de base de datos para cada solicitud y la cierra al finalizar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Proveedor de dependencia para FastAPI (asíncrono).
    Crea una nueva sesión de base de datos asíncrona para cada solicitud y la cierra al finalizar.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Importar todos los modelos aquí para que se registren con SQLAlchemy
# Esto debe hacerse después de definir Base
from app.models import *  # noqa

# Funciones de utilidad para la base de datos

def create_tables():
    """
    Crea todas las tablas definidas en los modelos.
    Esto solo debe usarse para pruebas o configuración inicial.
    Para migraciones, usa Alembic.
    """
    Base.metadata.create_all(bind=engine)

async def async_create_tables():
    """
    Versión asíncrona de create_tables.
    Crea todas las tablas definidas en los modelos de forma asíncrona.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def drop_tables():
    """
    Elimina todas las tablas de la base de datos.
    ¡Usar con precaución! Solo para pruebas.
    """
    Base.metadata.drop_all(bind=engine)

async def async_drop_tables():
    """
    Versión asíncrona de drop_tables.
    Elimina todas las tablas de la base de datos de forma asíncrona.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Configuración de sesión con alcance (para compatibilidad con código existente)
SessionScoped = scoped_session(SessionLocal)
