import os
from typing import Generator
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# Configuración de logging
import logging
logger = logging.getLogger(__name__)

# Crear la clase base para los modelos
Base = declarative_base()

# Configuración de la sesión de SQLAlchemy
class Database:
    def __init__(self, database_url: str = None):
        """Inicializa la conexión a la base de datos."""
        self.database_url = None
        self.engine = None
        self.SessionLocal = None
        self.set_url(database_url or self._get_database_url())
    
    def set_url(self, database_url: str) -> None:
        """Configura o actualiza la URL de la base de datos."""
        self.database_url = database_url
        logger.info(f"Configurando conexión a la base de datos: {self._obfuscate_url(self.database_url)}")
        
        # Cerrar el motor existente si lo hay
        if self.engine:
            self.engine.dispose()
        
        # Crear el nuevo motor
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=300,  # Reciclar conexiones cada 5 minutos
            echo=True  # Habilita el logging de SQL
        )
        
        # Configurar la sesión
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        logger.info("Conexión a la base de datos configurada correctamente")
    
    def _get_database_url(self) -> str:
        """Obtiene la URL de la base de datos desde las variables de entorno."""
        return os.getenv("DATABASE_URL", "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db")
    
    def _obfuscate_url(self, url: str) -> str:
        """Oculta las credenciales en la URL para logging."""
        from urllib.parse import urlparse, ParseResult
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
    
    def get_db(self) -> Generator[Session, None, None]:
        """Obtiene una sesión de base de datos."""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def get_engine(self) -> Engine:
        """Obtiene el motor de SQLAlchemy."""
        return self.engine

# Crear instancia de la base de datos
database = Database()

# Importar modelos para que sean detectados por Alembic
from app.models import *  # noqa
