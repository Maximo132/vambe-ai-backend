from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.ext.declarative import declared_attr
from ..core.config import settings

# Crear el motor de SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verifica que la conexión esté activa antes de usarla
    pool_recycle=3600,   # Recicla conexiones después de 1 hora
    pool_size=5,         # Número de conexiones a mantener en el pool
    max_overflow=10,     # Número máximo de conexiones adicionales a crear
    echo=settings.DEBUG  # Muestra las consultas SQL en consola
)

# Crear una fábrica de sesiones
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Evita que las instancias se expiren después del commit
)

# Crear una sesión con alcance
SessionScoped = scoped_session(SessionLocal)

# Base para los modelos
Base = declarative_base()

def get_db():
    """
    Proveedor de dependencia para FastAPI.
    Crea una nueva sesión de base de datos para cada solicitud y la cierra al finalizar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Importar todos los modelos aquí para que se registren con SQLAlchemy
from app.models import *  # noqa

def create_tables():
    """
    Crea todas las tablas definidas en los modelos.
    Esto solo debe usarse para pruebas o configuración inicial.
    Para migraciones, usa Alembic.
    """
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """
    Elimina todas las tablas de la base de datos.
    ¡Usar con precaución! Solo para pruebas.
    """
    Base.metadata.drop_all(bind=engine)
